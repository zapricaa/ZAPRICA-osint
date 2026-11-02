import json
import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import TaskEnvelope, FindingsPackage
from app.agents.workers.terminal_workers import (
    CliOsintWorker,
    NetworkIntelligenceWorker,
    MetadataAnalysisWorker,
    FileDocumentProcessingWorker
)
from app.terminal.terminal_manager import terminal_manager
from app.services.evidence_service import EvidenceService


class TerminalHeadAgent:
    """Sub-Head agent managing controlled command-line, Docker sandboxing, and network intelligence."""

    @classmethod
    async def execute_task(
        cls,
        session: AsyncSession,
        task: TaskEnvelope,
        workspace_id: uuid.UUID,
    ) -> FindingsPackage:
        investigation_id = uuid.UUID(task.investigation_id)
        capability = task.capability

        # Select tool corresponding to capability
        tool_id = task.allowed_tool_ids[0] if task.allowed_tool_ids else capability

        try:
            # 1. Execute task via dedicated worker architecture
            if tool_id == "dns_lookup":
                target = task.input.get("target") or task.input.get("domain", "")
                res = await NetworkIntelligenceWorker.run_dns(task.task_id, target, record_type=task.input.get("record_type", "A"))
            elif tool_id == "whois_lookup":
                target = task.input.get("target") or task.input.get("domain", "")
                res = await NetworkIntelligenceWorker.run_whois(task.task_id, target)
            elif tool_id == "metadata_extractor":
                target = task.input.get("target") or task.input.get("file_uri", "")
                res = await MetadataAnalysisWorker.extract_metadata(task.task_id, target)
            else:
                res = await CliOsintWorker.run(task.task_id, tool_id, task.input)

            # 2. Store raw execution evidence artifact
            result_payload = {
                "tool_id": tool_id,
                "command_name": res.command_name,
                "status": res.status,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "exit_code": res.exit_code,
                "duration_ms": res.duration_ms,
                "data": res.data,
            }
            raw_bytes = json.dumps(result_payload, indent=2).encode("utf-8")

            artifact = await EvidenceService.store_evidence(
                session=session,
                workspace_id=workspace_id,
                investigation_id=investigation_id,
                data_bytes=raw_bytes,
                media_type="application/json",
                collected_by="terminal_worker",
                source_url=f"cli://{tool_id}",
                source_locator=f"{tool_id}:{task.input.get('target', '')}",
                task_id=uuid.UUID(task.task_id) if task.task_id else None,
                metadata_json={
                    "tool_id": tool_id,
                    "exit_code": res.exit_code,
                    "duration_ms": res.duration_ms
                }
            )

            # 3. Process into structured findings
            findings = []
            target_str = task.input.get("target") or task.input.get("domain") or ""

            if tool_id == "dns_lookup":
                records = res.data.get("records", [])
                for ip in records:
                    f = await EvidenceService.process_and_create_finding(
                        session=session,
                        workspace_id=workspace_id,
                        investigation_id=investigation_id,
                        finding_type="network_infrastructure",
                        title=f"Resolved IP: {ip}",
                        summary=f"Domain {target_str} resolves to IP address {ip}",
                        raw_value=ip,
                        evidence_artifact_id=artifact.id,
                        source_url=f"dns://{target_str}",
                        source_locator="DNS A Record",
                        task_id=uuid.UUID(task.task_id) if task.task_id else None,
                        confidence_level="high",
                        confidence_reason="Authoritative DNS lookup via sandboxed worker"
                    )
                    findings.append({
                        "id": str(f.id),
                        "finding_type": f.finding_type,
                        "title": f.title,
                        "normalized_value": f.normalized_value,
                        "confidence_level": f.confidence_level
                    })

            elif tool_id == "whois_lookup":
                f = await EvidenceService.process_and_create_finding(
                    session=session,
                    workspace_id=workspace_id,
                    investigation_id=investigation_id,
                    finding_type="domain_info",
                    title=f"Domain Registration: {target_str}",
                    summary=f"Domain registered via {res.data.get('registrar', 'Public Registry')}",
                    raw_value=target_str,
                    evidence_artifact_id=artifact.id,
                    source_url=f"whois://{target_str}",
                    source_locator="WHOIS Registry",
                    task_id=uuid.UUID(task.task_id) if task.task_id else None,
                    confidence_level="high"
                )
                findings.append({
                    "id": str(f.id),
                    "finding_type": f.finding_type,
                    "title": f.title,
                    "normalized_value": f.normalized_value,
                    "confidence_level": f.confidence_level
                })

            elif tool_id == "metadata_extractor":
                f = await EvidenceService.process_and_create_finding(
                    session=session,
                    workspace_id=workspace_id,
                    investigation_id=investigation_id,
                    finding_type="metadata",
                    title=f"Extracted Document Metadata: {target_str}",
                    summary=res.stdout[:200],
                    raw_value=res.stdout[:500],
                    evidence_artifact_id=artifact.id,
                    source_url=f"file://{target_str}",
                    source_locator="ExifTool Metadata",
                    task_id=uuid.UUID(task.task_id) if task.task_id else None,
                    confidence_level="high"
                )
                findings.append({
                    "id": str(f.id),
                    "finding_type": f.finding_type,
                    "title": f.title,
                    "normalized_value": f.normalized_value,
                    "confidence_level": f.confidence_level
                })

            return FindingsPackage(
                investigation_id=str(investigation_id),
                subhead_agent="terminal_head",
                status="succeeded" if findings else "no_findings",
                findings=findings,
                evidence_artifacts=[{
                    "id": str(artifact.id),
                    "storage_uri": artifact.storage_uri,
                    "sha256": artifact.sha256,
                    "media_type": artifact.media_type
                }],
                execution_summary=result_payload
            )

        except Exception as e:
            return FindingsPackage(
                investigation_id=str(investigation_id),
                subhead_agent="terminal_head",
                status="failed",
                warnings=[f"Terminal execution error: {str(e)}"]
            )
