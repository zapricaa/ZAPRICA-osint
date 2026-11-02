"""API endpoints for unified 3-Tier Multi-Agent Fleet observation and supervision."""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_user
from app.models.users import User
from app.core.safe_mode import safe_mode_controller
from app.browser.session_manager import browser_session_manager
from app.terminal.terminal_manager import terminal_manager

router = APIRouter(prefix="/agents", tags=["Multi-Agent Fleet & Supervision"])


@router.get("/status")
async def get_agent_fleet_status(
    current_user: User = Depends(get_current_user),
):
    """
    Returns unified status across all three management agents:
    1. Main Head Agent (Strategic planning, AI Brain model, reasoning state)
    2. Browser Head Agent (Dedicated browser session, auth confirmation, tabs)
    3. Terminal Head Agent (Docker sandbox state, tool gateway status)
    """
    safe_status = safe_mode_controller.get_status()
    browser_sessions = browser_session_manager.list_sessions(user_id=str(current_user.id))
    active_browser = browser_sessions[0] if browser_sessions else None
    terminal_status = terminal_manager.get_environment_status()

    return {
        "fleet": {
            "main_head": {
                "name": "Main Head AI Agent",
                "role": "Master Strategic Planner & Synthesizer",
                "status": safe_status["agents_state"].get("main_head", "IDLE"),
                "model": "gemini-3.8-flash",
                "orchestrator": "LangGraph StateGraph",
                "untrusted_data_defense": "Enforced",
            },
            "browser_head": {
                "name": "Browser Head AI Agent",
                "role": "Web Reconnaissance & Dedicated Browser Supervisor",
                "status": active_browser.status.value if active_browser else safe_status["agents_state"].get("browser_head", "IDLE"),
                "model": "gemini-3.5-flash-lite",
                "automation_engine": "Playwright Persistent Context",
                "active_session": active_browser.model_dump() if active_browser else None,
                "automation_enabled": safe_status.get("browser_automation_enabled", False),
            },
            "terminal_head": {
                "name": "Terminal Head AI Agent",
                "role": "CLI & Tool Gateway Supervisor",
                "status": safe_status["agents_state"].get("terminal_head", "IDLE"),
                "model": "gemini-3.5-flash-lite",
                "execution_sandbox": "Docker Disposable Container",
                "terminal_execution_enabled": safe_status.get("terminal_execution_enabled", False),
                "docker_available": terminal_status.get("docker_sandbox_available", False),
                "host_execution_blocked": True,
            },
        },
        "safe_startup_mode": safe_status["safe_mode"],
        "workers_state": safe_status["workers_state"],
    }


@router.get("/{agent_id}/workers")
async def get_agent_workers(
    agent_id: str,
    current_user: User = Depends(get_current_user),
):
    """Returns specialized workers supervised by the given agent."""
    agent_id_low = agent_id.lower().strip()

    if agent_id_low in ("main_head", "main"):
        return {
            "agent_id": "main_head",
            "workers": [
                {"name": "Objective Parser Worker", "type": "ai_reasoning"},
                {"name": "Deterministic Scope Gate Worker", "type": "security_gate"},
                {"name": "DAG Task Planner Worker", "type": "ai_reasoning"},
                {"name": "Correlation & Synthesis Worker", "type": "ai_reasoning"},
            ]
        }
    elif agent_id_low in ("browser_head", "browser"):
        return {
            "agent_id": "browser_head",
            "workers": [
                {"name": "Playwright Persistent Navigation Worker", "type": "browser_automation"},
                {"name": "DOM Content & Metadata Extractor", "type": "html_parsing"},
                {"name": "SSRF Network Egress Firewall", "type": "network_security"},
                {"name": "Viewport Screenshot Capture Worker", "type": "evidence_collection"},
            ]
        }
    elif agent_id_low in ("terminal_head", "terminal"):
        return {
            "agent_id": "terminal_head",
            "workers": [
                {"name": "CLI OSINT Worker", "type": "docker_isolated"},
                {"name": "Authorized Network Intelligence Worker", "type": "docker_isolated"},
                {"name": "Metadata Analysis Worker", "type": "docker_isolated"},
                {"name": "File & Document Processing Worker", "type": "docker_isolated"},
                {"name": "Data Cleaning & Sanitization Worker", "type": "deterministic"},
                {"name": "Data Normalization Worker", "type": "deterministic"},
                {"name": "Duplicate Detection Worker", "type": "deterministic"},
                {"name": "Sorting & Indexing Worker", "type": "deterministic"},
            ]
        }
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found.")
