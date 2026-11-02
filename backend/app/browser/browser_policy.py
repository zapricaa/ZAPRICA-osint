"""Website automation policy engine enforcing policy rules (AUTOMATED_ALLOWED, HUMAN_ASSISTED_ONLY, API_ONLY, BLOCKED)."""

import fnmatch
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from fastapi import HTTPException, status


class PolicyType(str, Enum):
    AUTOMATED_ALLOWED = "AUTOMATED_ALLOWED"
    HUMAN_ASSISTED_ONLY = "HUMAN_ASSISTED_ONLY"
    API_ONLY = "API_ONLY"
    BLOCKED = "BLOCKED"


class AutomationPolicyRules(BaseModel):
    policy_type: PolicyType
    browser_automation: bool = True
    automated_queries: bool = True
    automated_extraction: bool = True
    agent_site_control: bool = True
    manual_user_access: bool = True
    manual_result_import: bool = True
    notes: Optional[str] = None


class BrowserPolicyEngine:
    """Manages and checks automation policies for target domains and tools."""

    # Default policy table
    _STATIC_POLICIES: Dict[str, AutomationPolicyRules] = {
        # Epieos special handling requirement (Section 2.6)
        "epieos.com": AutomationPolicyRules(
            policy_type=PolicyType.HUMAN_ASSISTED_ONLY,
            browser_automation=False,
            automated_queries=False,
            automated_extraction=False,
            agent_site_control=False,
            manual_user_access=True,
            manual_result_import=True,
            notes="Epieos: Investigator manually operates website, searches, and imports results. Automated queries/scraping prohibited."
        ),
        "*.epieos.com": AutomationPolicyRules(
            policy_type=PolicyType.HUMAN_ASSISTED_ONLY,
            browser_automation=False,
            automated_queries=False,
            automated_extraction=False,
            agent_site_control=False,
            manual_user_access=True,
            manual_result_import=True,
            notes="Epieos wildcard: Manual operator access only."
        ),
        "*.gov": AutomationPolicyRules(
            policy_type=PolicyType.HUMAN_ASSISTED_ONLY,
            browser_automation=False,
            automated_queries=False,
            automated_extraction=False,
            agent_site_control=False,
            manual_user_access=True,
            manual_result_import=True,
            notes="Government domains require explicit investigator manual control."
        ),
        "*.mil": AutomationPolicyRules(
            policy_type=PolicyType.BLOCKED,
            browser_automation=False,
            automated_queries=False,
            automated_extraction=False,
            agent_site_control=False,
            manual_user_access=False,
            manual_result_import=False,
            notes="Military domains are blocked by default."
        ),
    }

    @classmethod
    def get_policy_for_domain(cls, domain: str) -> AutomationPolicyRules:
        domain_lower = domain.lower().strip()
        if "://" in domain_lower:
            domain_lower = domain_lower.split("://", 1)[1].split("/", 1)[0]
        if ":" in domain_lower:
            domain_lower = domain_lower.split(":", 1)[0]

        # Exact match check
        if domain_lower in cls._STATIC_POLICIES:
            return cls._STATIC_POLICIES[domain_lower]

        # Pattern match check
        for pattern, policy in cls._STATIC_POLICIES.items():
            if fnmatch.fnmatch(domain_lower, pattern):
                return policy

        # Default fallback is AUTOMATED_ALLOWED for public targets within scope
        return AutomationPolicyRules(
            policy_type=PolicyType.AUTOMATED_ALLOWED,
            browser_automation=True,
            automated_queries=True,
            automated_extraction=True,
            agent_site_control=True,
            manual_user_access=True,
            manual_result_import=True,
            notes="Default policy: Automated public data extraction permitted within authorized scope."
        )

    @classmethod
    def register_policy(cls, domain_pattern: str, policy: AutomationPolicyRules):
        cls._STATIC_POLICIES[domain_pattern.lower().strip()] = policy

    @classmethod
    def enforce_action(cls, domain: str, action: str) -> AutomationPolicyRules:
        """
        Enforces that the requested browser action is permitted for the given domain.
        action can be:
        - "manual_navigate"
        - "automated_query"
        - "automated_extract"
        - "agent_site_control"
        - "manual_import"
        """
        policy = cls.get_policy_for_domain(domain)

        if policy.policy_type == PolicyType.BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Automation Policy Violation: Domain '{domain}' is BLOCKED ({policy.notes or 'Access Forbidden'})."
            )

        action_map = {
            "automated_query": "automated_queries",
            "automated_queries": "automated_queries",
            "automated_extract": "automated_extraction",
            "automated_extraction": "automated_extraction",
            "agent_site_control": "agent_site_control",
        }

        if action in action_map:
            attr = action_map[action]
            if not policy.browser_automation or not getattr(policy, attr, False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Automation Policy Violation: Domain '{domain}' is configured as '{policy.policy_type.value}'. "
                        f"Automated action '{action}' is strictly prohibited. (Reason: {policy.notes})"
                    )
                )

        if action in ("manual_navigate", "manual_user_access") and not policy.manual_user_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Policy Violation: Manual access to domain '{domain}' is prohibited."
            )

        if action in ("manual_import", "manual_result_import") and not policy.manual_result_import:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Policy Violation: Manual result import for domain '{domain}' is prohibited."
            )

        return policy
