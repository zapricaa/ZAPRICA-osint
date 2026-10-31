# ZAPRICA Implementation Status

Last Updated: 2026-10-31

## Overview
ZAPRICA is transitioning from documentation blueprint to an enterprise-grade AI-powered OSINT investigation platform.

---

## Phase Breakdown & Status

| Phase | Description | Status | Progress | Notes |
|---|---|---|---|---|
| **Phase 0** | Repository Inspection & Engineering Plan | Completed | 100% | Analyzed docs, identified inconsistencies, formulated plan & trackers. |
| **Phase 1** | Project Setup & Foundation | Completed | 100% | Backend venv configured, all packages installed, frontend scaffolded, `.env.example`. |
| **Phase 2** | Database Models, Migrations & Core Repositories | Completed | 100% | SQLAlchemy 2.0 async models (19 entities), Alembic async migration verified, unit tests passing. |
| **Phase 3** | Authentication, RBAC & Workspaces | In Progress | 10% | Schemas, AuthService, JWT, workspace scoping, and role enforcement. |
| **Phase 4** | Core REST API & SSE Event Streaming | Pending | 0% | Implementing `/v1/` routes matching `API_SPEC.yaml`, error schemas, SSE streaming. |
| **Phase 5** | Evidence Storage & Deterministic Processors | Pending | 0% | S3 / Local storage with SHA-256, normalization, cleaning, deduplication workers. |
| **Phase 6** | Main Head AI Agent (LangGraph) | Pending | 0% | Planning, scope gating, task decomposition, progress monitoring, report synthesis. |
| **Phase 7** | Browser Head Agent & Playwright Workers | Pending | 0% | Isolated browser contexts, SSRF egress filter, page metadata/content extraction. |
| **Phase 8** | Terminal Head Agent & Sandboxed CLI Adapters | Pending | 0% | Fixed tool adapters, schema validation, no arbitrary shell, timeout enforcement. |
| **Phase 9** | TIMS (Tool Intelligence & Management System) | Pending | 0% | Tool registration, playbooks, isolated test validation, admin approval workflow. |
| **Phase 10** | Findings Correlation & Report Generation | Pending | 0% | Evidence provenance linkage, conflict detection, markdown/JSON/CSV export. |
| **Phase 11** | Frontend Dashboard & Investigation Workspace | Pending | 0% | Next.js App Router, investigation UI, agent monitor, evidence explorer, TIMS admin. |
| **Phase 12** | Security Hardening & Acceptance Verification | Pending | 0% | Verification against all test scenarios in `ACCEPTANCE_CRITERIA.md`. |
| **Phase 13** | Deployment & Packaging | Pending | 0% | Production Dockerfiles, docker-compose, CI workflows, deployment runbook. |

---

## Acceptance Criteria Verification Matrix

| ID | Title | Status | Automated Test |
|---|---|---|---|
| AC-AUTH-01 | Unauthenticated user cannot access investigations | Pending | `tests/test_auth.py` |
| AC-AUTH-02 | User cannot read another workspace's investigation | Pending | `tests/test_workspace_isolation.py` |
| AC-AUTH-03 | Viewer cannot start an investigation | Pending | `tests/test_rbac.py` |
| AC-AUTH-04 | Admin action is audited | Pending | `tests/test_audit.py` |
| AC-INV-01 | Create investigation with scope | Pending | `tests/test_investigations.py` |
| AC-INV-02 | Reject empty or malformed scope | Pending | `tests/test_investigations.py` |
| AC-INV-03 | Enforce scope at execution time | Pending | `tests/test_scope_enforcement.py` |
| AC-INV-04 | Scope expiry stops new work | Pending | `tests/test_scope_enforcement.py` |
| AC-MAIN-01 | Main Head creates typed plan | Pending | `tests/test_main_head.py` |
| AC-MAIN-02 | Browser task routes to Browser Head | Pending | `tests/test_routing.py` |
| AC-MAIN-03 | Terminal task routes to Terminal Head | Pending | `tests/test_routing.py` |
| AC-MAIN-04 | LLM cannot expand scope | Pending | `tests/test_main_head.py` |
| AC-AGENT-01 | Worker reports to its own Sub-Head | Pending | `tests/test_subheads.py` |
| AC-AGENT-02 | Sub-Head returns findings package to Main Head | Pending | `tests/test_subheads.py` |
| AC-AGENT-03 | No findings is not failure | Pending | `tests/test_workers.py` |
| AC-AGENT-04 | Partial failure is visible | Pending | `tests/test_workers.py` |
| AC-EVD-01 | Raw evidence is immutable | Pending | `tests/test_evidence.py` |
| AC-EVD-02 | Finding has provenance | Pending | `tests/test_evidence.py` |
| AC-EVD-03 | Duplicate processing is deterministic | Pending | `tests/test_processing.py` |
| AC-EVD-04 | Conflicting sources are not silently merged | Pending | `tests/test_correlation.py` |
| AC-TIMS-01 | New tool starts as draft | Pending | `tests/test_tims.py` |
| AC-TIMS-02 | Documentation converted to draft playbook | Pending | `tests/test_tims.py` |
| AC-TIMS-03 | Tool version must pass isolated validation | Pending | `tests/test_tims.py` |
| AC-TIMS-04 | Approval is separate from validation | Pending | `tests/test_tims.py` |
| AC-TIMS-05 | Only assigned agents discover tool | Pending | `tests/test_tims.py` |
| AC-TIMS-06 | Revocation blocks execution | Pending | `tests/test_tims.py` |
| AC-TIMS-07 | Version update is immutable | Pending | `tests/test_tims.py` |
| AC-SEC-01 | Arbitrary shell text is rejected | Pending | `tests/test_security.py` |
| AC-SEC-02 | Browser cannot reach private address | Pending | `tests/test_security.py` |
| AC-SEC-03 | Prompt injection is treated as data | Pending | `tests/test_security.py` |
| AC-SEC-04 | Resource limits stop runaway work | Pending | `tests/test_security.py` |
| AC-REPORT-01 | Report distinguishes evidence from inference | Pending | `tests/test_reports.py` |
| AC-REPORT-02 | Report includes source provenance | Pending | `tests/test_reports.py` |
| AC-REPORT-03 | Incomplete investigation is not presented as complete | Pending | `tests/test_reports.py` |
| AC-REPORT-04 | Export is authorized | Pending | `tests/test_reports.py` |
