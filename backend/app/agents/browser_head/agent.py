import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import TaskEnvelope, FindingsPackage
from app.agents.browser_head.playwright_worker import PlaywrightBrowserWorker
from app.services.evidence_service import EvidenceService
from app.agents.workers.processors import DataCleaner, DataNormalizer, DuplicateDetector, DataClassifier


class BrowserHeadAgent:
    """Sub-Head agent managing browser automation and website intelligence."""

    @classmethod
    async def execute_task(
        cls,
        session: AsyncSession,
        task: TaskEnvelope,
        workspace_id: uuid.UUID,
    ) -> FindingsPackage:
        investigation_id = uuid.UUID(task.investigation_id)
        target = task.input.get("target") or task.input.get("url")
        if not target:
            return FindingsPackage(
                investigation_id=str(investigation_id),
                subhead_agent="browser_head",
                status="failed",
                warnings=["No target URL specified in task input."]
            )

        target_url = target if target.startswith("http") else f"https://{target}"

        try:
            # 1. Fetch via browser worker with SSRF egress enforcement
            raw_bytes, extracted = await PlaywrightBrowserWorker.extract_website_intelligence(
                target_url=target_url,
                timeout_seconds=task.budget.get("max_runtime_seconds", 30)
            )

            # 2. Store immutable evidence artifact (AC-EVD-01)
            artifact = await EvidenceService.store_evidence(
                session=session,
                workspace_id=workspace_id,
                investigation_id=investigation_id,
                data_bytes=raw_bytes,
                media_type="text/html",
                collected_by="browser_worker",
                source_url=target_url,
                source_locator="DOM Root",
                task_id=uuid.UUID(task.task_id) if task.task_id else None,
                metadata_json={
                    "http_status": extracted.get("http_status"),
                    "resolved_ips": extracted.get("resolved_ips", []),
                }
            )

            # 3. Process extracted attributes into candidate findings
            candidate_findings: List[Dict[str, Any]] = []

            # Page Title
            if extracted.get("title"):
                candidate_findings.append({
                    "finding_type": "domain_info",
                    "title": f"Website Title: {extracted['title'][:60]}",
                    "summary": extracted["title"],
                    "normalized_value": DataCleaner.sanitize_untrusted_snippet(extracted["title"], 100),
                    "confidence_level": "high",
                    "confidence_reason": "Extracted from verified HTML <title> tag",
                    "sources": [{"source_url": target_url, "source_locator": "<title>"}]
                })

            # Tech Stack clues
            for tech in extracted.get("tech_stack", []):
                val = tech.get("value", "")
                norm_val = DataNormalizer.normalize_tech_stack_name(val)
                candidate_findings.append({
                    "finding_type": "tech_stack",
                    "title": f"Web Technology: {norm_val}",
                    "summary": f"Identified {tech.get('type')} signature: {val}",
                    "normalized_value": norm_val,
                    "confidence_level": "high",
                    "confidence_reason": f"Observed in HTTP header/meta tag '{tech.get('type')}'",
                    "sources": [{"source_url": target_url, "source_locator": tech.get("type")}]
                })

            # Contacts (emails)
            for contact in extracted.get("contacts", []):
                norm_email = DataNormalizer.normalize_email(contact.get("value", ""))
                if norm_email:
                    candidate_findings.append({
                        "finding_type": "contact",
                        "title": f"Contact Email: {norm_email}",
                        "summary": f"Discovered email address on public page: {norm_email}",
                        "normalized_value": norm_email,
                        "confidence_level": "high",
                        "confidence_reason": "Direct text match on public webpage",
                        "sources": [{"source_url": target_url, "source_locator": "Page Body"}]
                    })

            # 4. Deterministic Deduplication (AC-EVD-03)
            deduped_findings, _ = DuplicateDetector.deduplicate(candidate_findings)

            # 5. Persist Findings & Provenance (AC-EVD-02)
            persisted_findings = []
            for f in deduped_findings:
                finding_model = await EvidenceService.process_and_create_finding(
                    session=session,
                    workspace_id=workspace_id,
                    investigation_id=investigation_id,
                    finding_type=f["finding_type"],
                    title=f["title"],
                    summary=f["summary"],
                    raw_value=f["normalized_value"],
                    evidence_artifact_id=artifact.id,
                    source_url=target_url,
                    source_locator=f["sources"][0]["source_locator"] if f.get("sources") else None,
                    task_id=uuid.UUID(task.task_id) if task.task_id else None,
                    confidence_level=f.get("confidence_level", "medium"),
                    confidence_reason=f.get("confidence_reason"),
                )
                persisted_findings.append({
                    "id": str(finding_model.id),
                    "finding_type": finding_model.finding_type,
                    "title": finding_model.title,
                    "summary": finding_model.summary,
                    "normalized_value": finding_model.normalized_value,
                    "confidence_level": finding_model.confidence_level,
                    "sources": [{"source_url": target_url, "evidence_artifact_id": str(artifact.id)}]
                })

            return FindingsPackage(
                investigation_id=str(investigation_id),
                subhead_agent="browser_head",
                status="succeeded" if persisted_findings else "no_findings",
                findings=persisted_findings,
                evidence_artifacts=[{
                    "id": str(artifact.id),
                    "storage_uri": artifact.storage_uri,
                    "sha256": artifact.sha256,
                    "media_type": artifact.media_type
                }],
                execution_summary={
                    "http_status": extracted.get("http_status"),
                    "resolved_ips": extracted.get("resolved_ips", []),
                    "links_count": len(extracted.get("external_links", [])),
                }
            )

        except Exception as e:
            return FindingsPackage(
                investigation_id=str(investigation_id),
                subhead_agent="browser_head",
                status="failed",
                warnings=[f"Browser worker error: {str(e)}"]
            )
