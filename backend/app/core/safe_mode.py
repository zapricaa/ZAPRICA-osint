"""Safe Application Startup Mode controller for ZAPRICA."""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class SafeModeState(BaseModel):
    safe_mode: bool = Field(default_factory=lambda: settings.ZAPRICA_SAFE_MODE)
    terminal_execution_enabled: bool = Field(default_factory=lambda: settings.TERMINAL_EXECUTION_ENABLED)
    auto_investigation_enabled: bool = Field(default_factory=lambda: settings.AUTO_INVESTIGATION_ENABLED)
    auto_tool_installation_enabled: bool = Field(default_factory=lambda: settings.AUTO_TOOL_INSTALLATION)
    agents_state: Dict[str, str] = Field(
        default_factory=lambda: {
            "main_head": "IDLE",
            "browser_head": "IDLE",
            "terminal_head": "IDLE",
        }
    )
    workers_state: str = "DISABLED"
    isolation_backend: str = "docker_sandboxed_non_root"
    fail_closed_active: bool = True


class SafeModeController:
    """Controls Safe Startup Mode, agent idle states, and administrative overrides."""

    def __init__(self):
        self._state = SafeModeState()
        logger.info(
            "SafeModeController initialized: safe_mode=%s, terminal_execution_enabled=%s, agents=IDLE, workers=DISABLED",
            self._state.safe_mode,
            self._state.terminal_execution_enabled,
        )

    @property
    def is_safe_mode(self) -> bool:
        return self._state.safe_mode

    @property
    def is_terminal_execution_enabled(self) -> bool:
        return self._state.terminal_execution_enabled

    @property
    def is_auto_investigation_enabled(self) -> bool:
        return self._state.auto_investigation_enabled

    @property
    def is_auto_tool_installation_enabled(self) -> bool:
        return self._state.auto_tool_installation_enabled

    def get_status(self) -> Dict[str, Any]:
        return self._state.model_dump()

    def enable_terminal_execution(self, admin_username: str, reason: str) -> None:
        """Administratively enable terminal execution with audit attribution."""
        self._state.terminal_execution_enabled = True
        logger.warning(
            "TERMINAL EXECUTION ENABLED by admin '%s'. Reason: %s",
            admin_username,
            reason,
        )

    def disable_terminal_execution(self, admin_username: str) -> None:
        """Administratively disable terminal execution."""
        self._state.terminal_execution_enabled = False
        logger.info("TERMINAL EXECUTION DISABLED by admin '%s'", admin_username)

    def set_safe_mode(self, enabled: bool, admin_username: str) -> None:
        """Toggle safe mode globally."""
        self._state.safe_mode = enabled
        if enabled:
            # If re-enabling safe mode, also disable terminal execution
            self._state.terminal_execution_enabled = False
            self._state.workers_state = "DISABLED"
            self._state.agents_state = {
                "main_head": "IDLE",
                "browser_head": "IDLE",
                "terminal_head": "IDLE",
            }
        logger.info("Safe mode set to %s by admin '%s'", enabled, admin_username)

    def set_agent_state(self, agent_name: str, state: str) -> None:
        self._state.agents_state[agent_name] = state

    def set_workers_state(self, state: str) -> None:
        self._state.workers_state = state


# Global safe mode controller singleton
safe_mode_controller = SafeModeController()

