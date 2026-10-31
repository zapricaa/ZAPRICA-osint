import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.investigations import Investigation
from app.models.evidence import Finding, FindingSource
from app.models.reports import Report


class ReportService:
    """Findings correlation, conflict analysis, and report generation service."""

    @classmethod
    async def generate_investigation_report(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> Report:
        # 1. Fetch investigation and verify workspace scope
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
            raise HTTPException(status_code=404, detail="Investigation not found in workspace.")

        # 2. Fetch all findings with sources (AC-REPORT-02)
        f_stmt = (
            select(Finding)
            .where(
                and_(
                    Finding.investigation_id == investigation_id,
                    Finding.workspace_id == workspace_id
                )
            )
            .options(selectinload(Finding.sources))
            .order_by(Finding.confidence_level.desc(), Finding.created_at.asc())
        )
        findings = list((await session.scalars(f_stmt)).all())

        # 3. Separate observed facts from inferences (AC-REPORT-01)
        observed_facts = []
        inferred_findings = []
        conflicts = []

        seen_attributes: Dict[str, Finding] = {}

        for f in findings:
            finding_repr = {
                "id": str(f.id),
                "type": f.finding_type,
                "title": f.title,
                "value": f.normalized_value,
                "summary": f.summary,
                "confidence": f.confidence_level,
                "verification_status": f.verification_status,
                "sources": [
                    {
                        "source_url": s.source_url,
                        "source_locator": s.source_locator,
                        "observed_at": s.observed_at.isoformat(),
                        "relationship": s.relationship
                    }
                    for s in f.sources
                ]
            }

            # Conflict Detection (AC-EVD-04): Check if conflicting values exist for same attribute
            attr_key = f"{f.finding_type}:{f.title.lower()}"
            if attr_key in seen_attributes:
                prev = seen_attributes[attr_key]
                if prev.normalized_value != f.normalized_value:
                    conflicts.append({
                        "attribute": f.title,
                        "conflict_detail": f"Source 1 reported '{prev.normalized_value}' while Source 2 reported '{f.normalized_value}'.",
                        "sources": finding_repr["sources"] + [
                            {"source_url": s.source_url, "source_locator": s.source_locator}
                            for s in prev.sources
                        ]
                    })
            else:
                seen_attributes[attr_key] = f

            if f.confidence_level == "high" or f.verification_status == "supported":
                observed_facts.append(finding_repr)
            else:
                inferred_findings.append(finding_repr)

        # 4. Determine next report version
        v_stmt = select(func.max(Report.version)).where(Report.investigation_id == investigation_id)
        latest_v = await session.scalar(v_stmt) or 0
        new_version = latest_v + 1

        # 5. Handle Incomplete / Partial Investigation notice (AC-REPORT-03)
        is_partial = inv.status in ["paused", "failed", "running", "queued"]
        status_label = "partial" if is_partial else "finalized"
        limitations = (
            "Investigation was not marked completed; findings represent partial observations."
            if is_partial else
            "All findings are limited strictly to public, authorized sources within approved scope."
        )

        report_json = {
            "target": inv.scope.allowed_targets if inv.scope else [],
            "purpose": inv.scope.purpose if inv.scope else "",
            "investigation_status": inv.status,
            "is_partial_report": is_partial,
            "observed_facts": observed_facts,
            "inferred_findings": inferred_findings,
            "conflicts_detected": conflicts,
            "limitations": limitations,
            "methodology": "Automated multi-agent OSINT collection with deterministic verification",
        }

        report = Report(
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            version=new_version,
            status=status_label,
            title=f"OSINT Report v{new_version}: {inv.title}",
            summary=f"Analysis identified {len(observed_facts)} verified facts, {len(inferred_findings)} inferences, and {len(conflicts)} source conflicts.",
            report_json=report_json,
            created_by_agent="report_service",
            created_at=datetime.now(timezone.utc),
            finalized_at=datetime.now(timezone.utc) if not is_partial else None
        )
        session.add(report)
        await session.commit()
        return report

    @classmethod
    async def export_json(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> str:
        """Export latest report as formatted JSON string (AC-REPORT-04)."""
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
        report = await session.scalar(stmt)
        if not report:
            raise HTTPException(status_code=404, detail="No reports available for this investigation.")

        return json.dumps(report.report_json, indent=2)

    @classmethod
    async def export_csv(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
    ) -> str:
        """Export findings as CSV string (AC-REPORT-04)."""
        f_stmt = (
            select(Finding)
            .where(
                and_(
                    Finding.investigation_id == investigation_id,
                    Finding.workspace_id == workspace_id
                )
            )
            .options(selectinload(Finding.sources))
            .order_by(Finding.created_at.desc())
        )
        findings = list((await session.scalars(f_stmt)).all())

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Finding ID", "Type", "Title", "Normalized Value", "Confidence", "Status", "Sources"])

        for f in findings:
            sources_str = "; ".join(s.source_url or s.source_locator or "" for s in f.sources)
            writer.writerow([
                str(f.id),
                f.finding_type,
                f.title,
                f.normalized_value or "",
                f.confidence_level,
                f.verification_status,
                sources_str
            ])

        return output.getvalue()
