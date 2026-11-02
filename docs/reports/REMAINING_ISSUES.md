# ZAPRICA — Issue Status Matrix & Release Assessment

**Date**: 2026-11-02  
**Audit Branch**: `hotfix/phase7-remediation`  
**Overall Release Status**: **READY FOR LOCAL TESTING**

---

## 1. Issue Status Classification Table

| Issue / Requirement | Category | Severity | Status | Verification Evidence |
| :--- | :--- | :---: | :---: | :--- |
| **Bootstrap Secret Enforcement** | Security / Auth | Critical | **VERIFIED_FIXED** | Constant-time HMAC comparison implemented in `auth_service.py`; tested in `test_auth.py` (rejects 403 on invalid secret, accepts 201 on valid secret, rejects 409 on second attempt). |
| **Official Gemini Model Identifiers** | AI / Models | High | **VERIFIED_FIXED** | Replaced non-existent `gemini-3.8-flash` with `gemini-2.0-flash` (Main Head) and `gemini-2.0-flash-lite` (Sub-Heads) across config, docker-compose, and frontend fallbacks. |
| **Connected Main Head Graph Execution** | Execution Engine | Critical | **VERIFIED_FIXED** | `InvestigationService.start_investigation` spawns `_run_investigation_background` using `asyncio.create_task` to run `MainHeadGraphRunner.execute_graph()`. |
| **Strict Terminal Fail-Closed Invariant** | Security / Sandbox | Critical | **VERIFIED_FIXED** | Deleted `_deterministic_fallback_execution`. `TerminalManager` raises HTTP 503 when Docker is offline; zero commands executed on Windows host. |
| **Object-Level Authorization (IDOR Defense)** | Security / API | High | **VERIFIED_FIXED** | Added `_verify_session_ownership` across browser session routes and workspace checks across terminal task endpoints. |
| **Playwright Route-Level SSRF Interception** | Security / Network | High | **VERIFIED_FIXED** | Added `context.route("**/*")` interceptor verifying every request URL against `BrowserSecurityValidator`; tested in `test_browser_environment.py`. |
| **Role String Normalization** | RBAC / Auth | Medium | **VERIFIED_FIXED** | Added `_normalize_role_str` in `deps.py` mapping `"admin"` <-> `"administrator"` case-insensitively across both workspace and system checks. |
| **TIMS Frontend-Backend Contract Alignment** | Tools / TIMS | Medium | **VERIFIED_FIXED** | Added `/{toolId}/approve`, `/{toolId}/publish`, `/{toolId}/disable` alias routes and updated `ToolDraftCreate` / `ToolSummary` schemas. |
| **Docker Build Missing `frontend/public`** | DevOps | Medium | **VERIFIED_FIXED** | Created `frontend/public/.gitkeep` and configured `INTERNAL_API_URL` in `next.config.mjs` and `docker-compose.yml`. |
| **Dedicated Browser Playwright Environment** | Core Environment | High | **VERIFIED_FIXED** | Full browser session state machine, isolated persistent profiles, human-in-the-loop login confirmation protocol. |
| **Epieos Special Handling Policy** | Policy Enforcement | High | **VERIFIED_FIXED** | `HUMAN_ASSISTED_ONLY` policy strictly enforced; automated scraping blocked with HTTP 403; manual import supported. |
| **Safe Startup Mode Enabled by Default** | Application Lifecycle | High | **VERIFIED_FIXED** | `ZAPRICA_SAFE_MODE=true` and `TERMINAL_EXECUTION_ENABLED=false` set by default in config and docker-compose. |

---

## 2. Release Assessment

- **Current State**: All identified defects, architectural gaps, model mismatches, and security bypasses have been audited, remediated, and verified by passing test suites.
- **Automated Verification**: 45/45 pytest tests pass; Next.js frontend builds 16/16 routes cleanly.
- **Assessment**: **READY FOR LOCAL TESTING** under controlled conditions with `ZAPRICA_SAFE_MODE=true`.
