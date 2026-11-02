import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.database import async_session_factory
from app.models.investigations import Investigation, InvestigationScope
from app.models.tasks import Task
from app.models.evidence import EvidenceArtifact, Finding, FindingSource
from app.models.reports import Report, AuditEvent
from app.schemas.investigations import InvestigationCreate, InvestigationOut, InvestigationScopeOut
from app.core.events import event_bus, InvestigationEvent

logger = logging.getLogger("zaprica.investigations")


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class InvestigationService:

    @staticmethod
    def _validate_scope_targets(targets: List[str]) -> List[str]:
        """Validate target domain / host syntax. Rejects empty, whitespace, or invalid targets."""
        if not targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Investigation scope must contain at least one valid allowed target."
            )

        cleaned_targets = []
        domain_pattern = re.compile(
            r"^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
        )
        ip_pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$")

        for t in targets:
            cleaned = t.strip().lower()
            if not cleaned:
                continue
            # Strip scheme if accidentally provided
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                cleaned = cleaned.split("://", 1)[1].split("/", 1)[0]

            if not (domain_pattern.match(cleaned) or ip_pattern.match(cleaned)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid target format: '{t}'. Target must be a valid domain name, wildcard (*.example.com), or IP/CIDR."
                )
            cleaned_targets.append(cleaned)

        if not cleaned_targets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid targets found in scope definition."
            )
        return cleaned_targets

    @classmethod
    async def create_investigation(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        data: InvestigationCreate,
    ) -> Investigation:
        # Validate scope targets (AC-INV-02)
        validated_targets = cls._validate_scope_targets(data.scope.allowed_targets)

        # 1. Create Investigation
        investigation = Investigation(
            workspace_id=workspace_id,
            created_by=user_id,
            title=data.title.strip(),
            objective=data.objective.strip(),
            investigation_type=data.investigation_type,
            status="draft",
            priority=data.priority,
        )
        session.add(investigation)
        await session.flush()

        # 2. Create Scope
        expires_at = data.scope.expires_at or (datetime.now(timezone.utc) + timedelta(days=30))
        scope = InvestigationScope(
            investigation_id=investigation.id,
            workspace_id=workspace_id,
            purpose=data.scope.purpose.strip(),
            allowed_targets=validated_targets,
            allowed_operations=data.scope.allowed_operations,
            denied_targets=data.scope.denied_targets,
            expires_at=expires_at,
            policy_version="1.0"
        )
        session.add(scope)

        # 3. Create Audit Record (AC-AUTH-04)
        audit = AuditEvent(
            workspace_id=workspace_id,
            actor_type="user",
            actor_id=str(user_id),
            action="investigation_created",
            resource_type="investigation",
            resource_id=investigation.id,
            investigation_id=investigation.id,
            decision="allow",
            metadata_redacted={
                "title": investigation.title,
                "targets": validated_targets,
            }
        )
        session.add(audit)
        await session.commit()

        # Reload with scope
        return await cls.get_investigation(session, workspace_id, investigation.id)

    @classmethod
    async def get_investigation(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Investigation:
        stmt = (
            select(Investigation)
            .where(
                and_(
                    Investigation.id == investigation_id,
                    Investigation.workspace_id == workspace_id
                )
            )
            .options(selectinload(Investigation.scope))
        )
        inv = await session.scalar(stmt)
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investigation not found in the authorized workspace."
            )
        return inv

    @classmethod
    async def list_investigations(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[Investigation], int]:
        filters = [Investigation.workspace_id == workspace_id]
        if status_filter:
            filters.append(Investigation.status == status_filter)

        total_stmt = select(func.count(Investigation.id)).where(and_(*filters))
        total = await session.scalar(total_stmt) or 0

        query_stmt = (
            select(Investigation)
            .where(and_(*filters))
            .options(selectinload(Investigation.scope))
            .order_by(Investigation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.scalars(query_stmt)
        return list(result.all()), total

    @classmethod
    async def start_investigation(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Investigation:
        inv = await cls.get_investigation(session, workspace_id, investigation_id)

        # Check state transitions
        if inv.status not in ["draft", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot start investigation in status '{inv.status}'."
            )

        # Validate Scope Expiry (AC-INV-04)
        if inv.scope and ensure_utc(inv.scope.expires_at) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Investigation scope has expired. Please renew or re-authorize scope before starting."
            )

        inv.status = "queued"
        inv.started_at = datetime.now(timezone.utc)
        await session.commit()

        # Emit SSE Event
        await event_bus.publish(
            InvestigationEvent(
                investigation_id=str(inv.id),
                event_type="investigation_started",
                data={"status": inv.status, "started_at": inv.started_at.isoformat()}
            )
        )

        # Dispatch background execution of Main Head LangGraph pipeline
        asyncio.create_task(
            cls._run_investigation_background(workspace_id, user_id, investigation_id)
        )

        return inv

    @classmethod
    async def _run_investigation_background(
        cls,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> None:
        """Background worker executing Main Head LangGraph pipeline."""
        async with async_session_factory() as session:
            try:
                # Update status to running
                inv = await cls.get_investigation(session, workspace_id, investigation_id)
                inv.status = "running"
                await session.commit()

                await event_bus.publish(
                    InvestigationEvent(
                        investigation_id=str(investigation_id),
                        event_type="investigation_status_change",
                        data={"status": "running"}
                    )
                )

                # Execute LangGraph Main Head workflow
                await cls.execute_graph(session, workspace_id, user_id, investigation_id)

            except Exception as e:
                logger.error("Error executing investigation graph for %s: %s", investigation_id, e)
                try:
                    inv = await cls.get_investigation(session, workspace_id, investigation_id)
                    inv.status = "failed"
                    inv.completed_at = datetime.now(timezone.utc)
                    await session.commit()

                    await event_bus.publish(
                        InvestigationEvent(
                            investigation_id=str(investigation_id),
                            event_type="investigation_failed",
                            data={"status": "failed", "error": str(e)}
                        )
                    )
                except Exception as rollback_err:
                    logger.error("Failed to record investigation failure state: %s", rollback_err)

    @classmethod
    async def execute_graph(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Execute the LangGraph Main Head workflow."""
        inv = await cls.get_investigation(session, workspace_id, investigation_id)
        from app.agents.main_head.graph import MainHeadGraphRunner
        runner = MainHeadGraphRunner.build_graph(session)
        target = inv.scope.allowed_targets[0] if (inv.scope and inv.scope.allowed_targets) else "example.com"
        initial_state = {
            "investigation_id": str(inv.id),
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "target": target,
            "objective": inv.objective,
            "scope": {
                "allowed_targets": inv.scope.allowed_targets if inv.scope else [],
                "allowed_operations": inv.scope.allowed_operations if inv.scope else [],
                "purpose": inv.scope.purpose if inv.scope else "",
            },
            "plan": {},
            "tasks": [],
            "findings_packages": [],
            "consolidated_findings": [],
            "report_id": None,
            "status": "queued",
            "errors": [],
            "audit_events": []
        }
        return await runner.ainvoke(initial_state)

    @classmethod
    async def pause_investigation(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Investigation:
        inv = await cls.get_investigation(session, workspace_id, investigation_id)
        if inv.status not in ["running", "planning", "queued"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot pause investigation currently in status '{inv.status}'."
            )

        inv.status = "paused"
        await session.commit()

        await event_bus.publish(
            InvestigationEvent(
                investigation_id=str(inv.id),
                event_type="investigation_paused",
                data={"status": inv.status}
            )
        )
        return inv

    @classmethod
    async def resume_investigation(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Investigation:
        inv = await cls.get_investigation(session, workspace_id, investigation_id)
        if inv.status != "paused":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot resume investigation in status '{inv.status}'. Must be 'paused'."
            )

        # Check scope expiry again on resume (AC-INV-04)
        if inv.scope and ensure_utc(inv.scope.expires_at) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Investigation scope has expired during pause. Re-authorization required."
            )

        inv.status = "running"
        await session.commit()

        await event_bus.publish(
            InvestigationEvent(
                investigation_id=str(inv.id),
                event_type="investigation_resumed",
                data={"status": inv.status}
            )
        )
        return inv

    @classmethod
    async def cancel_investigation(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Investigation:
        inv = await cls.get_investigation(session, workspace_id, investigation_id)
        if inv.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Investigation is already in terminal state '{inv.status}'."
            )

        inv.status = "cancelled"
        inv.completed_at = datetime.now(timezone.utc)
        await session.commit()

        await event_bus.publish(
            InvestigationEvent(
                investigation_id=str(inv.id),
                event_type="investigation_cancelled",
                data={"status": inv.status, "completed_at": inv.completed_at.isoformat()}
            )
        )
        return inv

    @classmethod
    async def list_tasks(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> List[Task]:
        # Validate investigation belongs to workspace
        await cls.get_investigation(session, workspace_id, investigation_id)
        stmt = (
            select(Task)
            .where(
                and_(
                    Task.investigation_id == investigation_id,
                    Task.workspace_id == workspace_id
                )
            )
            .order_by(Task.created_at.asc())
        )
        result = await session.scalars(stmt)
        return list(result.all())

    @classmethod
    async def list_findings(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
        verification_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Tuple[List[Finding], int]:
        await cls.get_investigation(session, workspace_id, investigation_id)
        filters = [
            Finding.investigation_id == investigation_id,
            Finding.workspace_id == workspace_id
        ]
        if verification_status:
            filters.append(Finding.verification_status == verification_status)

        total_stmt = select(func.count(Finding.id)).where(and_(*filters))
        total = await session.scalar(total_stmt) or 0

        stmt = (
            select(Finding)
            .where(and_(*filters))
            .options(selectinload(Finding.sources))
            .order_by(Finding.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.scalars(stmt)
        return list(result.all()), total

    @classmethod
    async def list_evidence(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> List[EvidenceArtifact]:
        await cls.get_investigation(session, workspace_id, investigation_id)
        stmt = (
            select(EvidenceArtifact)
            .where(
                and_(
                    EvidenceArtifact.investigation_id == investigation_id,
                    EvidenceArtifact.workspace_id == workspace_id
                )
            )
            .order_by(EvidenceArtifact.collected_at.desc())
        )
        result = await session.scalars(stmt)
        return list(result.all())

    @classmethod
    async def list_reports(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> List[Report]:
        await cls.get_investigation(session, workspace_id, investigation_id)
        stmt = (
            select(Report)
            .where(
                and_(
                    Report.investigation_id == investigation_id,
                    Report.workspace_id == workspace_id
                )
            )
            .order_by(Report.version.desc())
        )
        result = await session.scalars(stmt)
        return list(result.all())
