"""Investigation (case) management routes."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    Investigation, Entity, Evidence, ActivityLog,
    EntityRelationship, InvestigationStatus, EntityType
)
from app.schemas import (
    InvestigationCreate, InvestigationUpdate, InvestigationResponse,
    InvestigationListResponse, EntityResponse, EvidenceCreate, EvidenceResponse,
    ActivityLogResponse, RelationshipCreate, RelationshipResponse,
    GraphResponse, GraphNode, GraphEdge
)

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


def _normalize_entity(value: str, entity_type: str) -> str:
    """Normalize entity values for deduplication."""
    value = value.strip()
    if entity_type in ("domain", "email"):
        value = value.lower()
    if entity_type == "domain":
        value = value.rstrip(".")
        if value.startswith("www."):
            value = value[4:]
    if entity_type == "ip_address":
        parts = value.split(".")
        if len(parts) == 4:
            try:
                value = ".".join(str(int(p)) for p in parts)
            except ValueError:
                pass
    if entity_type == "url":
        value = value.lower().rstrip("/")
    if entity_type == "file_hash":
        value = value.lower()
    return value


@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(data: InvestigationCreate, db: AsyncSession = Depends(get_db)):
    inv = Investigation(
        name=data.name,
        description=data.description,
        seed_entity=data.seed_entity,
        seed_entity_type=EntityType(data.seed_entity_type),
        authorized_use_confirmed=data.authorized_use_confirmed,
        config=data.config,
    )
    db.add(inv)

    # Create the seed entity
    normalized = _normalize_entity(data.seed_entity, data.seed_entity_type)
    seed = Entity(
        investigation_id=inv.id,
        entity_type=EntityType(data.seed_entity_type),
        value=data.seed_entity,
        normalized_value=normalized,
        source="user_input",
    )
    db.add(seed)

    # Log creation
    log = ActivityLog(
        investigation_id=inv.id,
        action="investigation_created",
        actor="user",
        details={"seed_entity": data.seed_entity, "seed_type": data.seed_entity_type},
    )
    db.add(log)

    await db.commit()
    await db.refresh(inv)

    return InvestigationResponse(
        id=inv.id, name=inv.name, description=inv.description,
        seed_entity=inv.seed_entity, seed_entity_type=inv.seed_entity_type.value,
        status=inv.status.value, authorized_use_confirmed=inv.authorized_use_confirmed,
        created_at=inv.created_at, updated_at=inv.updated_at,
        entity_count=1, evidence_count=0,
    )


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Investigation).order_by(Investigation.updated_at.desc())
    if status:
        query = query.where(Investigation.status == InvestigationStatus(status))
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    investigations = result.scalars().all()

    # Get total count
    count_q = select(func.count(Investigation.id))
    if status:
        count_q = count_q.where(Investigation.status == InvestigationStatus(status))
    total = (await db.execute(count_q)).scalar() or 0

    items = []
    for inv in investigations:
        e_count = (await db.execute(
            select(func.count(Entity.id)).where(Entity.investigation_id == inv.id)
        )).scalar() or 0
        ev_count = (await db.execute(
            select(func.count(Evidence.id)).where(Evidence.investigation_id == inv.id)
        )).scalar() or 0
        items.append(InvestigationResponse(
            id=inv.id, name=inv.name, description=inv.description,
            seed_entity=inv.seed_entity, seed_entity_type=inv.seed_entity_type.value,
            status=inv.status.value, authorized_use_confirmed=inv.authorized_use_confirmed,
            created_at=inv.created_at, updated_at=inv.updated_at,
            entity_count=e_count, evidence_count=ev_count,
        ))

    return InvestigationListResponse(investigations=items, total=total)


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(investigation_id: str, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    e_count = (await db.execute(
        select(func.count(Entity.id)).where(Entity.investigation_id == inv.id)
    )).scalar() or 0
    ev_count = (await db.execute(
        select(func.count(Evidence.id)).where(Evidence.investigation_id == inv.id)
    )).scalar() or 0

    return InvestigationResponse(
        id=inv.id, name=inv.name, description=inv.description,
        seed_entity=inv.seed_entity, seed_entity_type=inv.seed_entity_type.value,
        status=inv.status.value, authorized_use_confirmed=inv.authorized_use_confirmed,
        created_at=inv.created_at, updated_at=inv.updated_at,
        entity_count=e_count, evidence_count=ev_count,
    )


@router.patch("/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: str, data: InvestigationUpdate, db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    if data.name is not None:
        inv.name = data.name
    if data.description is not None:
        inv.description = data.description
    if data.status is not None:
        inv.status = InvestigationStatus(data.status)
    if data.config is not None:
        inv.config = data.config
    inv.updated_at = datetime.now(timezone.utc)

    log = ActivityLog(
        investigation_id=inv.id, action="investigation_updated", actor="user",
        details=data.model_dump(exclude_none=True),
    )
    db.add(log)
    await db.commit()
    await db.refresh(inv)

    return await get_investigation(investigation_id, db)


@router.delete("/{investigation_id}", status_code=204)
async def delete_investigation(investigation_id: str, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    await db.delete(inv)
    await db.commit()


# --- Entities ---

@router.get("/{investigation_id}/entities", response_model=list[EntityResponse])
async def list_entities(investigation_id: str, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    result = await db.execute(
        select(Entity).where(Entity.investigation_id == investigation_id)
    )
    entities = result.scalars().all()
    return [EntityResponse(
        id=e.id, investigation_id=e.investigation_id, entity_type=e.entity_type.value,
        value=e.value, normalized_value=e.normalized_value, source=e.source,
        confidence=e.confidence, first_seen=e.first_seen, last_seen=e.last_seen,
        metadata=e.metadata_,
    ) for e in entities]


# --- Evidence ---

@router.post("/{investigation_id}/evidence", response_model=EvidenceResponse, status_code=201)
async def create_evidence(
    investigation_id: str, data: EvidenceCreate, db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    sha256 = None
    if data.raw_content:
        sha256 = hashlib.sha256(data.raw_content.encode("utf-8")).hexdigest()

    ev = Evidence(
        investigation_id=investigation_id,
        source_url=data.source_url,
        tool_name=data.tool_name,
        collection_method=data.collection_method,
        content_type=data.content_type,
        raw_content=data.raw_content,
        sha256_hash=sha256,
    )
    db.add(ev)

    log = ActivityLog(
        investigation_id=investigation_id,
        action="evidence_collected",
        actor="system",
        details={"tool": data.tool_name, "source": data.source_url},
    )
    db.add(log)

    await db.commit()
    await db.refresh(ev)

    return EvidenceResponse(
        id=ev.id, investigation_id=ev.investigation_id, source_url=ev.source_url,
        tool_name=ev.tool_name, collection_method=ev.collection_method,
        content_type=ev.content_type, sha256_hash=ev.sha256_hash,
        storage_ref=ev.storage_ref, collected_at=ev.collected_at, status=ev.status,
    )


@router.get("/{investigation_id}/evidence", response_model=list[EvidenceResponse])
async def list_evidence(investigation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Evidence).where(Evidence.investigation_id == investigation_id)
    )
    items = result.scalars().all()
    return [EvidenceResponse(
        id=e.id, investigation_id=e.investigation_id, source_url=e.source_url,
        tool_name=e.tool_name, collection_method=e.collection_method,
        content_type=e.content_type, sha256_hash=e.sha256_hash,
        storage_ref=e.storage_ref, collected_at=e.collected_at, status=e.status,
    ) for e in items]


# --- Activity Log ---

@router.get("/{investigation_id}/activity", response_model=list[ActivityLogResponse])
async def list_activity(investigation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.investigation_id == investigation_id)
        .order_by(ActivityLog.timestamp.desc())
    )
    items = result.scalars().all()
    return [ActivityLogResponse(
        id=a.id, investigation_id=a.investigation_id, action=a.action,
        actor=a.actor, details=a.details, timestamp=a.timestamp,
    ) for a in items]


# --- Relationships ---

@router.post("/{investigation_id}/relationships", response_model=RelationshipResponse, status_code=201)
async def create_relationship(
    investigation_id: str, data: RelationshipCreate, db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    rel = EntityRelationship(
        investigation_id=investigation_id,
        source_entity_id=data.source_entity_id,
        target_entity_id=data.target_entity_id,
        relationship_type=data.relationship_type,
        confidence=data.confidence,
        evidence_id=data.evidence_id,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)

    return RelationshipResponse(
        id=rel.id, source_entity_id=rel.source_entity_id,
        target_entity_id=rel.target_entity_id, relationship_type=rel.relationship_type.value,
        confidence=rel.confidence, evidence_id=rel.evidence_id, created_at=rel.created_at,
    )


# --- Graph ---

@router.get("/{investigation_id}/graph", response_model=GraphResponse)
async def get_graph(investigation_id: str, db: AsyncSession = Depends(get_db)):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    entities_result = await db.execute(
        select(Entity).where(Entity.investigation_id == investigation_id)
    )
    entities = entities_result.scalars().all()

    rels_result = await db.execute(
        select(EntityRelationship).where(EntityRelationship.investigation_id == investigation_id)
    )
    rels = rels_result.scalars().all()

    nodes = [GraphNode(
        id=e.id, label=e.value, entity_type=e.entity_type.value,
        value=e.normalized_value, confidence=e.confidence, metadata=e.metadata_,
    ) for e in entities]

    edges = [GraphEdge(
        id=r.id, source=r.source_entity_id, target=r.target_entity_id,
        relationship_type=r.relationship_type.value, confidence=r.confidence,
        evidence_id=r.evidence_id,
    ) for r in rels]

    return GraphResponse(nodes=nodes, edges=edges)
