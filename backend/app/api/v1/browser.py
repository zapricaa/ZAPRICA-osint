"""API endpoints for dedicated Playwright browser sessions, navigation, and human-in-the-loop authentication."""

import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role, get_db
from app.models.users import User
from app.models.browser import BrowserSession, BrowserProfile
from app.browser.browser_manager import browser_manager
from app.browser.session_manager import browser_session_manager, ActiveBrowserSessionState
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/browser", tags=["Browser Head & Dedicated Browser"])


class CreateBrowserSessionRequest(BaseModel):
    investigation_id: uuid.UUID
    profile_name: str = "default"
    headless: Optional[bool] = None


class NavigateBrowserRequest(BaseModel):
    target_url: str = Field(..., min_length=4, max_length=2000)
    wait_until: str = "domcontentloaded"
    timeout_ms: int = 30000


class ImportManualResultRequest(BaseModel):
    finding_type: str = "manual_intelligence"
    title: str = Field(..., min_length=3, max_length=200)
    summary: str
    raw_data: str
    source_url: str
    confidence_level: str = "high"


@router.post("/sessions", response_model=ActiveBrowserSessionState)
async def create_browser_session(
    payload: CreateBrowserSessionRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Starts or attaches a dedicated persistent browser session for an authorized investigation."""
    session_state = await browser_manager.start_session(
        investigation_id=payload.investigation_id,
        user_id=current_user.id,
        profile_name=payload.profile_name,
        headless=payload.headless,
    )

    # Persist in DB
    db_session = BrowserSession(
        id=uuid.UUID(session_state.session_id),
        investigation_id=payload.investigation_id,
        user_id=current_user.id,
        profile_id=uuid.UUID(session_state.profile_id),
        status=session_state.status.value,
        current_url=session_state.current_url,
        active_tab_count=session_state.active_tab_count,
        session_metadata=session_state.metadata,
    )
    # Check or create profile record
    prof = await db.scalar(
        select(BrowserProfile).where(
            BrowserProfile.user_id == current_user.id,
            BrowserProfile.profile_name == payload.profile_name,
        )
    )
    if not prof:
        prof = BrowserProfile(
            id=uuid.UUID(session_state.profile_id),
            user_id=current_user.id,
            workspace_id=current_user.workspace_id or uuid.uuid4(),
            profile_name=payload.profile_name,
            storage_path=f"data/browser_profiles/{current_user.id}/{payload.profile_name}",
        )
        db.add(prof)
        await db.flush()

    db_session.profile_id = prof.id
    db.add(db_session)
    await db.commit()

    return session_state


@router.get("/sessions", response_model=List[ActiveBrowserSessionState])
async def list_browser_sessions(
    current_user: User = Depends(get_current_user),
):
    """Lists active browser sessions for the current user."""
    return browser_session_manager.list_sessions(user_id=str(current_user.id))


@router.get("/sessions/{session_id}", response_model=ActiveBrowserSessionState)
async def get_browser_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves current status, active tabs, and navigation state of a browser session."""
    session = browser_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Browser session '{session_id}' not found.")
    return session


@router.post("/sessions/{session_id}/navigate")
async def navigate_browser(
    session_id: str,
    payload: NavigateBrowserRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
):
    """Navigates the dedicated browser to target_url with SSRF and website automation policy checks."""
    return await browser_manager.navigate(
        session_id=session_id,
        target_url=payload.target_url,
        wait_until=payload.wait_until,
        timeout_ms=payload.timeout_ms,
    )


@router.post("/sessions/{session_id}/confirm-authentication", response_model=ActiveBrowserSessionState)
async def confirm_authentication(
    session_id: str,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Operator explicitly marks that they have logged in and completed MFA in the dedicated browser.
    Sets status to USER_AUTHENTICATED.
    """
    state = await browser_manager.confirm_authentication(
        session_id=session_id,
        operator_username=current_user.username,
    )
    # Sync with DB
    db_sess = await db.scalar(select(BrowserSession).where(BrowserSession.id == uuid.UUID(session_id)))
    if db_sess:
        db_sess.status = state.status.value
        db_sess.auth_confirmed_by = current_user.id
        await db.commit()

    return state


@router.post("/sessions/{session_id}/screenshot")
async def capture_browser_screenshot(
    session_id: str,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Captures screenshot of current page as an immutable evidence artifact."""
    session_state = browser_session_manager.get_session(session_id)
    if not session_state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    screenshot_bytes = await browser_manager.capture_screenshot(session_id)
    inv_id = uuid.UUID(session_state.investigation_id)

    artifact = await EvidenceService.store_evidence(
        session=db,
        workspace_id=current_user.workspace_id or uuid.uuid4(),
        investigation_id=inv_id,
        data_bytes=screenshot_bytes,
        media_type="image/png",
        collected_by="browser_head",
        source_url=session_state.current_url or "browser://active-page",
        source_locator="Investigator Manual Screenshot",
        metadata_json={"session_id": session_id}
    )

    return {
        "status": "success",
        "evidence_id": str(artifact.id),
        "sha256": artifact.sha256,
        "storage_uri": artifact.storage_uri,
    }


@router.post("/sessions/{session_id}/import-manual-result")
async def import_manual_result(
    session_id: str,
    payload: ImportManualResultRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Special workflow for HUMAN_ASSISTED_ONLY sites (such as Epieos):
    Allows investigator to import results manually obtained and link them as verified findings.
    """
    session_state = browser_session_manager.get_session(session_id)
    if not session_state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    inv_id = uuid.UUID(session_state.investigation_id)
    raw_bytes = payload.raw_data.encode("utf-8")

    # 1. Store immutable raw artifact
    artifact = await EvidenceService.store_evidence(
        session=db,
        workspace_id=current_user.workspace_id or uuid.uuid4(),
        investigation_id=inv_id,
        data_bytes=raw_bytes,
        media_type="text/plain",
        collected_by="manual_investigator_import",
        source_url=payload.source_url,
        source_locator="Operator Manual Import",
        metadata_json={"session_id": session_id}
    )

    # 2. Persist Finding linked to artifact
    finding = await EvidenceService.process_and_create_finding(
        session=db,
        workspace_id=current_user.workspace_id or uuid.uuid4(),
        investigation_id=inv_id,
        finding_type=payload.finding_type,
        title=payload.title,
        summary=payload.summary,
        raw_value=payload.raw_data[:200],
        evidence_artifact_id=artifact.id,
        source_url=payload.source_url,
        source_locator="Operator Verified Import",
        confidence_level=payload.confidence_level,
        confidence_reason="Manually verified and imported by operator inside dedicated browser"
    )

    return {
        "status": "success",
        "artifact_id": str(artifact.id),
        "finding_id": str(finding.id),
        "sha256": artifact.sha256,
    }


@router.post("/sessions/{session_id}/stop")
async def stop_browser_session(
    session_id: str,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "ADMINISTRATOR", "INVESTIGATOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Closes dedicated browser context and stops session."""
    await browser_manager.close_session(session_id)
    db_sess = await db.scalar(select(BrowserSession).where(BrowserSession.id == uuid.UUID(session_id)))
    if db_sess:
        db_sess.status = BrowserSessionStatus.STOPPED.value
        await db.commit()

    return {"status": "stopped", "session_id": session_id}
