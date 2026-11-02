"""DCE (Data Collection Engine) Coordinator: Coordinates collectors, TIMS checks, and Evidence persistence."""

import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.adapters import (
    BaseCollectorAdapter,
    WhoisCollectorAdapter,
    DnsCollectorAdapter,
    HibpCollectorAdapter,
    TheHarvesterCollectorAdapter,
    SherlockCollectorAdapter,
    HoleheCollectorAdapter,
    SyntheticDemoCollectorAdapter,
)
from app.collection.contracts import CollectorType, TargetType, CollectorStatus, RawCollectorOutput
from app.collection.schemas import (
    CollectionJobRequest,
    CollectionJobResponse,
    CollectorCapabilityInfo,
)
from app.core.events import InvestigationEvent, event_bus
from app.models.evidence import EvidenceArtifact, Finding, FindingSource
from app.models.investigations import Investigation
from app.models.tasks import Task
from app.models.users import User
from app.models.workspaces import Workspace
from app.services.evidence_service import EvidenceService

logger = logging.getLogger("zaprica.collection.coordinator")


class DCECoordinator:
    """Coordinates OSINT data collection across CLI Docker sandboxes, authenticated APIs, and synthetic fixtures."""

    def __init__(self):
        self._adapters: Dict[str, BaseCollectorAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self):
        adapters = [
            WhoisCollectorAdapter(),
            DnsCollectorAdapter(),
            HibpCollectorAdapter(),
            TheHarvesterCollectorAdapter(),
            SherlockCollectorAdapter(),
            HoleheCollectorAdapter(),
            SyntheticDemoCollectorAdapter(),
        ]
        for a in adapters:
            self._adapters[a.tool_id] = a

    def get_adapter(self, tool_id: str) -> Optional[BaseCollectorAdapter]:
        return self._adapters.get(tool_id)

    def list_capabilities(self) -> List[CollectorCapabilityInfo]:
        """Returns metadata and readiness telemetry for all registered collectors."""
        capabilities = []
        for a in self._adapters.values():
            available, note = a.is_available()
            capabilities.append(
                CollectorCapabilityInfo(
                    tool_id=a.tool_id,
                    name=a.name,
                    description=a.description,
                    collector_type=a.collector_type,
                    supported_target_types=list(a.supported_target_types),
                    is_enabled=available,
                    requires_approval=a.requires_approval,
                    requires_api_key=a.requires_api_key,
                    is_available=available,
                    availability_note=note,
                )
            )
        return capabilities

    async def execute_collection(
        self,
        session: AsyncSession,
        request: CollectionJobRequest,
        current_user: User,
        workspace: Workspace,
    ) -> CollectionJobResponse:
        """
        Executes a scoped data collection job, verifies authorization, stores raw evidence,
        and generates unreviewed linked findings.
        """
        adapter = self.get_adapter(request.tool_id)
        if not adapter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DCE Error: Collector '{request.tool_id}' is not registered."
            )

        # 1. Verify Investigation exists and belongs to workspace
        inv = await session.scalar(
            select(Investigation).where(
                Investigation.id == request.investigation_id,
                Investigation.workspace_id == workspace.id
            )
        )
        if not inv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investigation not found in current workspace."
            )

        # 2. Scope Validation Check
        allowed_targets = [t.lower() for t in (inv.scope_json or {}).get("allowed_targets", [])]
        denied_targets = [t.lower() for t in (inv.scope_json or {}).get("denied_targets", [])]

        target_clean = request.target.strip().lower()
        if "://" in target_clean:
            target_clean = target_clean.split("://", 1)[1].split("/", 1)[0]

        # Check against denied targets
        if any(target_clean == d or (d.startswith("*.") and target_clean.endswith(d[2:])) for d in denied_targets):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope Violation: Target '{target_clean}' is in the investigation denylist."
            )

        # If allowed_targets is defined, check membership
        if allowed_targets and adapter.collector_type != CollectorType.SYNTHETIC:
            allowed = any(
                target_clean == a or (a.startswith("*.") and target_clean.endswith(a[2:])) or (a in target_clean)
                for a in allowed_targets
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Scope Violation: Target '{target_clean}' is not authorized in scope: {allowed_targets}"
                )

        # 3. Create parent Task record in database for audit provenance
        job_id = f"dce-{uuid.uuid4().hex[:10]}"
        db_task = Task(
            workspace_id=workspace.id,
            investigation_id=inv.id,
            requesting_agent="dce_coordinator",
            assigned_agent="terminal_head" if adapter.collector_type == CollectorType.CLI else "api_adapter",
            capability=adapter.tool_id,
            objective=f"Collect {adapter.name} for target '{request.target}'",
            input_json={"target": request.target, "options": request.options},
            allowed_tool_ids=[adapter.tool_id],
            status="running",
        )
        session.add(db_task)
        await session.commit()
        await session.refresh(db_task)

        # 4. Execute the Collector
        raw_output: RawCollectorOutput = await adapter.execute(
            target=request.target,
            options=request.options,
            task_id=str(db_task.id),
        )

        # 5. Evidence Persistence (Section E)
        media_type = "application/json" if adapter.collector_type == CollectorType.API else "text/plain"
        data_to_store = raw_output.raw_bytes if raw_output.raw_bytes else raw_output.stdout.encode("utf-8")

        artifact = await EvidenceService.store_evidence(
            session=session,
            workspace_id=workspace.id,
            investigation_id=inv.id,
            data_bytes=data_to_store,
            media_type=media_type,
            collected_by=adapter.tool_id,
            source_url=f"dce://{adapter.tool_id}/{target_clean}",
            source_locator=f"job_id={job_id};exit_code={raw_output.exit_code}",
            task_id=db_task.id,
            metadata_json={
                "tool_id": adapter.tool_id,
                "tool_version": raw_output.tool_version,
                "collector_type": adapter.collector_type.value,
                "duration_ms": raw_output.execution_duration_ms,
                "exit_code": raw_output.exit_code,
                "is_synthetic": raw_output.is_synthetic,
                "warnings": raw_output.warnings,
                "errors": raw_output.errors,
            }
        )

        # 6. Generate Linked Findings with unreviewed status
        finding_ids: List[uuid.UUID] = []
        parsed = raw_output.parsed_data

        if adapter.tool_id == "whois_lookup" and parsed.get("registrar"):
            finding = Finding(
                workspace_id=workspace.id,
                investigation_id=inv.id,
                task_id=db_task.id,
                finding_type="domain_info",
                title=f"WHOIS Registrar: {parsed.get('registrar')}",
                normalized_value=parsed.get("registrar"),
                summary=f"Domain registered via {parsed.get('registrar')}. Created: {parsed.get('creation_date')}, Expires: {parsed.get('expiration_date')}.",
                verification_status="unreviewed",
                confidence_level="high",
                confidence_reason="Official registry WHOIS record query via Linux whois utility.",
            )
            session.add(finding)
            await session.flush()
            session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="direct_output", confidence_weight=0.9))
            finding_ids.append(finding.id)

        elif adapter.tool_id == "dns_lookup" and parsed.get("records"):
            for rec in parsed.get("records", [])[:10]:  # Limit top 10 records as findings
                finding = Finding(
                    workspace_id=workspace.id,
                    investigation_id=inv.id,
                    task_id=db_task.id,
                    finding_type="network_intel",
                    title=f"DNS {rec.get('record_type')}: {rec.get('value')}",
                    normalized_value=rec.get("value"),
                    summary=f"Resolved DNS {rec.get('record_type')} record pointing to {rec.get('value')}.",
                    verification_status="unreviewed",
                    confidence_level="high",
                    confidence_reason="Direct authoritative DNS query using dig.",
                )
                session.add(finding)
                await session.flush()
                session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="direct_output", confidence_weight=0.95))
                finding_ids.append(finding.id)

        elif adapter.tool_id == "hibp" and parsed.get("breaches"):
            for b in parsed.get("breaches", []):
                finding = Finding(
                    workspace_id=workspace.id,
                    investigation_id=inv.id,
                    task_id=db_task.id,
                    finding_type="credential_leak",
                    title=f"Breach Exposure: {b.get('title')} ({b.get('breach_date')})",
                    normalized_value=b.get("domain"),
                    summary=f"Account exposed in {b.get('name')} breach on {b.get('breach_date')}. Compromised data classes: {', '.join(b.get('data_classes', []))}.",
                    verification_status="unreviewed",
                    confidence_level="high",
                    confidence_reason="Verified exposure record in Have I Been Pwned repository.",
                )
                session.add(finding)
                await session.flush()
                session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="direct_output", confidence_weight=0.9))
                finding_ids.append(finding.id)

        elif adapter.tool_id == "sherlock" and parsed.get("candidates"):
            for c in parsed.get("candidates", []):
                finding = Finding(
                    workspace_id=workspace.id,
                    investigation_id=inv.id,
                    task_id=db_task.id,
                    finding_type="contact",
                    title=f"Candidate Profile: {c.get('site_name')}",
                    normalized_value=c.get("profile_url"),
                    summary=f"Public profile URL candidate matching username: {c.get('profile_url')} on {c.get('site_name')}. (Note: Profile reuse is an indicator, not proof of identity).",
                    verification_status="unreviewed",
                    confidence_level="low",
                    confidence_reason="Public web profile match from Sherlock CLI scan.",
                )
                session.add(finding)
                await session.flush()
                session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="direct_output", confidence_weight=0.5))
                finding_ids.append(finding.id)

        elif adapter.tool_id == "theharvester":
            for sub in parsed.get("subdomains", []):
                finding = Finding(
                    workspace_id=workspace.id,
                    investigation_id=inv.id,
                    task_id=db_task.id,
                    finding_type="domain_info",
                    title=f"Subdomain: {sub}",
                    normalized_value=sub,
                    summary=f"Subdomain {sub} discovered via public passive sources.",
                    verification_status="unreviewed",
                    confidence_level="medium",
                    confidence_reason="Passive intelligence harvested by theHarvester.",
                )
                session.add(finding)
                await session.flush()
                session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="direct_output", confidence_weight=0.7))
                finding_ids.append(finding.id)

            for em in parsed.get("emails", []):
                finding = Finding(
                    workspace_id=workspace.id,
                    investigation_id=inv.id,
                    task_id=db_task.id,
                    finding_type="contact",
                    title=f"Discovered Email: {em}",
                    normalized_value=em,
                    summary=f"Public email address {em} associated with domain.",
                    verification_status="unreviewed",
                    confidence_level="medium",
                    confidence_reason="Passive intelligence harvested by theHarvester.",
                )
                session.add(finding)
                await session.flush()
                session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="direct_output", confidence_weight=0.7))
                finding_ids.append(finding.id)

        elif adapter.tool_id == "demo_collector" and parsed.get("findings"):
            for f_dict in parsed.get("findings", []):
                finding = Finding(
                    workspace_id=workspace.id,
                    investigation_id=inv.id,
                    task_id=db_task.id,
                    finding_type=f_dict.get("finding_type", "domain_info"),
                    title=f_dict.get("title", "Synthetic Finding"),
                    normalized_value=f_dict.get("value"),
                    summary=f"SYNTHETIC DEMO FINDING: {f_dict.get('value')}",
                    verification_status="unreviewed",
                    confidence_level=f_dict.get("confidence_level", "low"),
                    confidence_reason="Simulated finding generated by synthetic demo collector.",
                )
                session.add(finding)
                await session.flush()
                session.add(FindingSource(finding_id=finding.id, evidence_artifact_id=artifact.id, extraction_type="synthetic_fixture", confidence_weight=0.1))
                finding_ids.append(finding.id)

        # 7. Update Task status and commit all records
        db_task.status = "succeeded" if raw_output.status == CollectorStatus.SUCCESS else "failed"
        db_task.completed_at = datetime.now(timezone.utc)
        await session.commit()

        # 8. Publish event on EventBus
        await event_bus.publish(
            InvestigationEvent(
                investigation_id=str(inv.id),
                event_type="collector_completed",
                data={
                    "job_id": job_id,
                    "tool_id": adapter.tool_id,
                    "target": request.target,
                    "status": raw_output.status.value,
                    "findings_count": len(finding_ids),
                    "evidence_id": str(artifact.id),
                }
            )
        )

        return CollectionJobResponse(
            job_id=job_id,
            investigation_id=inv.id,
            tool_id=adapter.tool_id,
            target=request.target,
            target_type=request.target_type,
            status=raw_output.status,
            execution_duration_ms=raw_output.execution_duration_ms,
            evidence_artifact_id=artifact.id,
            evidence_sha256=artifact.sha256,
            finding_ids=finding_ids,
            data=raw_output.parsed_data,
            warnings=raw_output.warnings,
            errors=raw_output.errors,
            collected_at=raw_output.collected_at,
        )


dce_coordinator = DCECoordinator()

