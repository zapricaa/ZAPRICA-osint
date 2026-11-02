"""Browser Session State and Lifecycle Manager."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class BrowserSessionStatus(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    STARTING = "STARTING"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    AUTHENTICATING = "AUTHENTICATING"
    USER_AUTHENTICATED = "USER_AUTHENTICATED"
    READY = "READY"
    BUSY = "BUSY"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class ActiveBrowserSessionState(BaseModel):
    session_id: str
    investigation_id: str
    user_id: str
    profile_id: str
    status: BrowserSessionStatus = BrowserSessionStatus.DISCONNECTED
    current_url: Optional[str] = None
    active_tab_count: int = 0
    auth_confirmed: bool = False
    auth_confirmed_at: Optional[str] = None
    auth_confirmed_by: Optional[str] = None
    last_action_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    automation_policy: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BrowserSessionManager:
    """Tracks live in-memory browser sessions and state transitions."""

    def __init__(self):
        self._active_sessions: Dict[str, ActiveBrowserSessionState] = {}

    def register_session(
        self,
        session_id: uuid.UUID,
        investigation_id: uuid.UUID,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
    ) -> ActiveBrowserSessionState:
        s_id = str(session_id)
        state = ActiveBrowserSessionState(
            session_id=s_id,
            investigation_id=str(investigation_id),
            user_id=str(user_id),
            profile_id=str(profile_id),
            status=BrowserSessionStatus.STARTING,
        )
        self._active_sessions[s_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[ActiveBrowserSessionState]:
        return self._active_sessions.get(session_id)

    def list_sessions(self, user_id: Optional[str] = None) -> list[ActiveBrowserSessionState]:
        if user_id:
            return [s for s in self._active_sessions.values() if s.user_id == user_id]
        return list(self._active_sessions.values())

    def update_status(
        self,
        session_id: str,
        status: BrowserSessionStatus,
        current_url: Optional[str] = None,
        error_message: Optional[str] = None,
        tab_count: Optional[int] = None,
    ) -> Optional[ActiveBrowserSessionState]:
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        session.status = status
        session.last_action_at = datetime.now(timezone.utc).isoformat()
        if current_url is not None:
            session.current_url = current_url
        if error_message is not None:
            session.error_message = error_message
        if tab_count is not None:
            session.active_tab_count = tab_count

        return session

    def confirm_user_authenticated(self, session_id: str, confirmed_by: str) -> Optional[ActiveBrowserSessionState]:
        """Operator explicitly marks login challenge as completed inside the dedicated browser."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        now_str = datetime.now(timezone.utc).isoformat()
        session.status = BrowserSessionStatus.USER_AUTHENTICATED
        session.auth_confirmed = True
        session.auth_confirmed_at = now_str
        session.auth_confirmed_by = confirmed_by
        session.last_action_at = now_str

        return session

    def close_session(self, session_id: str) -> Optional[ActiveBrowserSessionState]:
        session = self._active_sessions.get(session_id)
        if session:
            session.status = BrowserSessionStatus.STOPPED
            session.last_action_at = datetime.now(timezone.utc).isoformat()
        return session


# Global singleton instance
browser_session_manager = BrowserSessionManager()
