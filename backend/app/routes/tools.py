"""Tool registry and execution routes — MCP-compatible JSON-RPC style."""
import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Investigation, Entity, Evidence, ActivityLog, EntityRelationship, EntityType, RelationshipType
from app.schemas import ToolResponse, ToolExecuteRequest, ToolExecuteResponse
from app.tools import TOOL_REGISTRY, execute_tool

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _normalize_entity(value: str, entity_type: str) -> str:
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
    return value


@router.get("", response_model=list[ToolResponse])
async def list_tools():
    """List available OSINT tools (MCP tools/list equivalent)."""
    tools = []
    for name, info in TOOL_REGISTRY.items():
        tools.append(ToolResponse(
            id=name, name=name, description=info["description"],
            category=info["category"], input_schema=info["input_schema"],
            enabled=True, requires_network=info["requires_network"],
            risk_level=info["risk_level"],
        ))
    return tools


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool_endpoint(req: ToolExecuteRequest, db: AsyncSession = Depends(get_db)):
    """Execute an OSINT tool (MCP tools/call equivalent)."""
    if req.tool_name not in TOOL_REGISTRY:
        raise HTTPException(404, f"Tool '{req.tool_name}' not found")

    result = await execute_tool(req.tool_name, req.parameters)

    evidence_id = None
    entities_found = 0

    # If linked to an investigation, store evidence and extract entities
    if req.investigation_id and "error" not in result:
        inv = await db.get(Investigation, req.investigation_id)
        if not inv:
            raise HTTPException(404, "Investigation not found")

        raw_json = json.dumps(result, sort_keys=True, default=str)
        sha256 = hashlib.sha256(raw_json.encode()).hexdigest()

        ev = Evidence(
            investigation_id=req.investigation_id,
            source_url=result.get("url") or result.get("domain") or result.get("hostname"),
            tool_name=req.tool_name,
            collection_method=f"tool:{req.tool_name}",
            content_type="application/json",
            raw_content=raw_json,
            sha256_hash=sha256,
        )
        db.add(ev)
        await db.flush()
        evidence_id = ev.id

        # Extract entities from results
        entities_found = await _extract_entities(db, req.investigation_id, result, ev.id)

        log = ActivityLog(
            investigation_id=req.investigation_id,
            action="tool_executed",
            actor="system",
            details={
                "tool": req.tool_name,
                "parameters": req.parameters,
                "entities_found": entities_found,
            },
        )
        db.add(log)
        await db.commit()

    return ToolExecuteResponse(
        success="error" not in result,
        tool_name=req.tool_name,
        result=result,
        error=result.get("error"),
        evidence_id=evidence_id,
        entities_found=entities_found,
    )


async def _extract_entities(
    db: AsyncSession, investigation_id: str, result: dict, evidence_id: str
) -> int:
    """Extract and store entities from tool results, with deduplication."""
    from sqlalchemy import select

    entities_added = 0
    tool = result.get("tool", "")

    # Get the seed entity to create relationships
    seed_q = await db.execute(
        select(Entity).where(
            Entity.investigation_id == investigation_id,
            Entity.source == "user_input"
        )
    )
    seed_entity = seed_q.scalars().first()

    entity_pairs = []  # (type, value) pairs to create

    if tool == "dns_lookup":
        records = result.get("records", [])
        record_type = result.get("record_type", "A")
        for rec in records:
            if record_type in ("A", "AAAA"):
                entity_pairs.append(("ip_address", rec, "resolves_to"))
            elif record_type == "MX":
                # MX records have priority prefix
                parts = rec.split()
                if len(parts) >= 2:
                    entity_pairs.append(("domain", parts[-1], "associated_with"))
                else:
                    entity_pairs.append(("domain", rec, "associated_with"))
            elif record_type == "NS":
                entity_pairs.append(("domain", rec, "associated_with"))
            elif record_type == "CNAME":
                entity_pairs.append(("domain", rec, "resolves_to"))

    elif tool == "tls_certificate":
        subject = result.get("subject", {})
        issuer = result.get("issuer", {})
        sans = result.get("subject_alt_names", [])
        if subject.get("commonName"):
            entity_pairs.append(("domain", subject["commonName"], "issued_to"))
        if issuer.get("organizationName"):
            entity_pairs.append(("organization", issuer["organizationName"], "associated_with"))
        for san in sans:
            if san.startswith("DNS:"):
                entity_pairs.append(("domain", san[4:], "associated_with"))

    elif tool == "rdap_lookup":
        nameservers = result.get("nameservers", [])
        for ns in nameservers:
            if ns:
                entity_pairs.append(("domain", ns, "associated_with"))
        for ent in result.get("entities", []):
            if ent.get("email"):
                entity_pairs.append(("email", ent["email"], "registered_by"))
            if ent.get("name"):
                entity_pairs.append(("person", ent["name"], "registered_by"))

    elif tool == "webpage_metadata":
        linked_domains = result.get("linked_domains", [])
        for domain in linked_domains[:10]:
            entity_pairs.append(("domain", domain, "mentions"))

    elif tool == "http_metadata":
        # Extract server info
        server = result.get("server")
        if server and server != "unknown":
            entity_pairs.append(("organization", server, "associated_with"))

    # Deduplicate and create entities + relationships
    for etype, evalue, rel_type in entity_pairs:
        normalized = _normalize_entity(evalue, etype)

        # Check for existing entity
        existing = await db.execute(
            select(Entity).where(
                Entity.investigation_id == investigation_id,
                Entity.entity_type == EntityType(etype),
                Entity.normalized_value == normalized,
            )
        )
        entity = existing.scalars().first()

        if not entity:
            entity = Entity(
                investigation_id=investigation_id,
                entity_type=EntityType(etype),
                value=evalue,
                normalized_value=normalized,
                source=f"tool:{result.get('tool', 'unknown')}",
            )
            db.add(entity)
            await db.flush()
            entities_added += 1

        # Create relationship from seed entity
        if seed_entity and entity.id != seed_entity.id:
            try:
                rel = EntityRelationship(
                    investigation_id=investigation_id,
                    source_entity_id=seed_entity.id,
                    target_entity_id=entity.id,
                    relationship_type=RelationshipType(rel_type),
                    evidence_id=evidence_id,
                )
                db.add(rel)
            except (ValueError, Exception):
                pass  # Skip if relationship type not in enum

    return entities_added
