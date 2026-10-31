from typing import TypedDict, List, Dict, Any, Optional


class InvestigationState(TypedDict, total=False):
    investigation_id: str
    workspace_id: str
    user_id: str
    target: str
    objective: str
    scope: Dict[str, Any]
    analysis: Dict[str, Any]
    plan: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    findings_packages: List[Dict[str, Any]]
    consolidated_findings: List[Dict[str, Any]]
    findings_analysis: Dict[str, Any]
    report_id: Optional[str]
    status: str
    errors: List[str]
    audit_events: List[str]
