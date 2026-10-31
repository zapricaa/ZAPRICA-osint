import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.evidence import EvidenceArtifact, Finding, FindingSource
from app.storage.factory import get_storage
from app.agents.workers.processors import DataCleaner, DataNormalizer, DuplicateDetector, DataClassifier


class EvidenceService:

    @classmethod
    async def store_evidence(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
        data_bytes: bytes,
        media_type: str,
        collected_by: str,
        source_url: Optional[str] = None,
        source_locator: Optional[str] = None,
        task_id: Optional[uuid.UUID] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> EvidenceArtifact:
        storage = get_storage()
        filename_hint = "snapshot.html" if "html" in media_type else "artifact.bin"
        storage_uri, sha256, byte_size = await storage.store(
            data=data_bytes,
            media_type=media_type,
            filename_hint=filename_hint
        )

        artifact = EvidenceArtifact(
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            task_id=task_id,
            storage_uri=storage_uri,
            media_type=media_type,
            byte_size=byte_size,
            sha256=sha256,
            source_url=source_url,
            source_locator=source_locator,
            collected_by=collected_by,
            collected_at=datetime.now(timezone.utc),
            captured_at=datetime.now(timezone.utc),
            integrity_status="verified",
            metadata_json=metadata_json or {}
        )
        session.add(artifact)
        await session.commit()
        return artifact

    @classmethod
    async def verify_artifact_integrity(
        cls, session: AsyncSession, artifact_id: uuid.UUID
    ) -> bool:
        """AC-EVD-01: Verify artifact content hash matches stored SHA-256."""
        artifact = await session.scalar(select(EvidenceArtifact).where(EvidenceArtifact.id == artifact_id))
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found.")

        storage = get_storage()
        valid = await storage.verify_integrity(artifact.storage_uri, artifact.sha256)
        if not valid and artifact.integrity_status != "tampered":
            artifact.integrity_status = "tampered"
            await session.commit()
        return valid

    @classmethod
    async def process_and_create_finding(
        cls,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
        finding_type: str,
        title: str,
        summary: str,
        raw_value: str,
        evidence_artifact_id: uuid.UUID,
        source_url: Optional[str] = None,
        source_locator: Optional[str] = None,
        task_id: Optional[uuid.UUID] = None,
        confidence_level: str = "medium",
        confidence_reason: Optional[str] = None,
    ) -> Finding:
        """Process derived finding, link to evidence artifact with full provenance."""
        # Clean & normalize value
        cleaned_summary = DataCleaner.sanitize_untrusted_snippet(summary)
        norm_val = raw_value.strip().lower()

        # Create finding
        finding = Finding(
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            task_id=task_id,
            finding_type=finding_type,
            title=title.strip(),
            normalized_value=norm_val,
            summary=cleaned_summary,
            verification_status="supported",
            confidence_level=confidence_level,
            confidence_reason=confidence_reason,
            first_observed_at=datetime.now(timezone.utc),
            last_observed_at=datetime.now(timezone.utc),
            processor_name="deterministic_pipeline",
            processor_version="1.0",
            derived_from=[str(evidence_artifact_id)]
        )
        session.add(finding)
        await session.flush()

        # Link source provenance
        source = FindingSource(
            finding_id=finding.id,
            evidence_artifact_id=evidence_artifact_id,
            source_url=source_url,
            source_locator=source_locator,
            relationship="supports",
            observed_at=datetime.now(timezone.utc)
        )
        session.add(source)
        await session.commit()

        # Return with sources loaded
        stmt = select(Finding).where(Finding.id == finding.id).options(selectinload(Finding.sources))
        return await session.scalar(stmt)
