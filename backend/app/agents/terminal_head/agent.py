import json
import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import TaskEnvelope, FindingsPackage
from app.agents.terminal_head.tool_gateway import tool_gateway
from app.services.evidence_service import EvidenceService


class TerminalHeadAgent:
    """Sub-Head agent managing controlled command-line and network intelligence."""

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
            # 1. Execute via controlled ToolGateway (AC-SEC-01 & AC-SEC-04)
            result = await tool_gateway.execute_tool(
                tool_id=tool_id,
                arguments=task.input,
                timeout_seconds=task.budget.get("max_runtime_seconds", 20)
            )

            # 2. Store raw artifact
            raw_bytes = json.dumps(result, indent=2).encode("utf-8")
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
                metadata_json={"tool_id": tool_id}
            )

            # 3. Process into findings
            findings = []
            if tool_id == "dns_lookup":
                for ip in result.get("records", []):
                    f = await EvidenceService.process_and_create_finding(
                        session=session,
                        workspace_id=workspace_id,
                        investigation_id=investigation_id,
                        finding_type="network_infrastructure",
                        title=f"Resolved IP: {ip}",
                        summary=f"Domain {result['target']} resolves to IP address {ip}",
                        raw_value=ip,
                        evidence_artifact_id=artifact.id,
                        source_url=f"dns://{result['target']}",
                        source_locator="DNS A Record",
                        task_id=uuid.UUID(task.task_id) if task.task_id else None,
                        confidence_level="high",
                        confidence_reason="Authoritative DNS lookup"
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
                    title=f"Domain Registration: {result['domain_name']}",
                    summary=f"Domain registered via {result['registrar']}",
                    raw_value=result["domain_name"],
                    evidence_artifact_id=artifact.id,
                    source_url=f"whois://{result['domain_name']}",
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
                execution_summary=result
            )

        except Exception as e:
            return FindingsPackage(
                investigation_id=str(investigation_id),
                subhead_agent="terminal_head",
                status="failed",
                warnings=[f"Terminal execution error: {str(e)}"]
            )
