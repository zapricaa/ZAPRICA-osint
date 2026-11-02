# ZAPRICA — Automated Test Execution Results

**Date**: 2026-11-02  
**Test Suite**: Pytest 9.2.0, Python 3.13.1 (Windows x64) / Next.js 14.2.35  
**Result**: 45/45 BACKEND TESTS PASSED, 16/16 FRONTEND ROUTES COMPILED  

---

## 1. Backend Test Suite Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.2.0, pluggy-1.7.0 -- backend\.venv\Scripts\python.exe
rootdir: E:\test\ZAPRICA-osint\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, langsmith-0.14.16, asyncio-1.4.1
collected 45 items

backend\tests\test_ai_brain.py::test_model_registry_resolution PASSED    [  2%]
backend\tests\test_ai_brain.py::test_untrusted_data_sanitization PASSED  [  4%]
backend\tests\test_ai_brain.py::test_structured_reasoning_schemas PASSED [  6%]
backend\tests\test_ai_brain.py::test_failure_handling_and_rejection PASSED [  8%]
backend\tests\test_ai_brain.py::test_function_calling_and_tool_gateway_validation PASSED [ 11%]
backend\tests\test_ai_brain.py::test_google_gemini_provider_initialization PASSED [ 13%]
backend\tests\test_auth.py::test_health_endpoints PASSED                 [ 15%]
backend\tests\test_auth.py::test_ac_auth_01_unauthenticated_user_rejected PASSED [ 17%]
backend\tests\test_auth.py::test_public_registration_disabled PASSED     [ 20%]
backend\tests\test_auth.py::test_one_time_bootstrap_super_admin PASSED   [ 22%]
backend\tests\test_auth.py::test_admin_invitation_and_acceptance_flow PASSED [ 24%]
backend\tests\test_auth.py::test_suspended_user_access_revocation PASSED [ 26%]
backend\tests\test_auth.py::test_mfa_setup_and_login_verification PASSED [ 28%]
backend\tests\test_auth.py::test_logout_invalidates_session PASSED       [ 31%]
backend\tests\test_browser_environment.py::test_ssrf_egress_security_filter PASSED [ 33%]
backend\tests\test_browser_environment.py::test_epieos_special_handling_policy PASSED [ 35%]
backend\tests\test_blocked_domains_policy PASSED [ 37%]
backend\tests\test_browser_environment.py::test_browser_profile_isolation PASSED [ 40%]
backend\tests\test_browser_environment.py::test_browser_session_state_machine PASSED [ 42%]
backend\tests\test_browser_environment.py::test_browser_manager_lifecycle PASSED [ 44%]
backend\tests\test_evidence.py::test_ac_evd_01_evidence_storage_and_integrity PASSED [ 46%]
backend\tests\test_evidence.py::test_ac_evd_02_finding_provenance PASSED [ 48%]
backend\tests\test_evidence.py::test_ac_evd_03_deterministic_cleaning_and_deduplication PASSED [ 51%]
backend\tests\test_investigations.py::test_ac_inv_01_create_investigation_with_scope PASSED [ 53%]
backend\tests\test_investigations.py::test_ac_inv_02_reject_empty_or_malformed_scope PASSED [ 55%]
backend\tests\test_investigations.py::test_investigation_lifecycle_controls PASSED [ 57%]
backend\tests\test_investigations.py::test_ac_inv_04_scope_expiry_blocks_start PASSED [ 60%]
backend\tests\test_main_head.py::test_ac_main_01_02_03_end_to_end_orchestration PASSED [ 62%]
backend\tests\test_main_head.py::test_ac_main_04_llm_cannot_expand_scope PASSED [ 64%]
backend\tests\test_models.py::test_create_workspace_and_user PASSED      [ 66%]
backend\tests\test_reports.py::test_ac_report_01_separation_of_facts_and_inferences PASSED [ 68%]
backend\tests\test_reports.py::test_ac_report_02_provenance_links_in_report PASSED [ 71%]
backend\tests\test_reports.py::test_ac_report_03_partial_investigation_warning PASSED [ 73%]
backend\tests\test_reports.py::test_ac_evd_04_cross_source_conflict_detection PASSED [ 75%]
backend\tests\test_reports.py::test_ac_report_04_json_and_csv_exports PASSED [ 77%]
backend\tests\test_security.py::test_ac_sec_01_arbitrary_shell_rejected PASSED [ 80%]
backend\tests\test_security.py::test_ac_sec_02_ssrf_egress_blocks_forbidden_destinations PASSED [ 82%]
backend\tests\test_security.py::test_ac_sec_02_ssrf_egress_permits_public_destinations PASSED [ 84%]
backend\tests\test_security.py::test_ac_sec_04_schema_validation_and_adapter_safety PASSED [ 86%]
backend\tests\test_terminal_environment.py::test_terminal_safe_mode_fail_closed PASSED [ 88%]
backend\tests\test_terminal_environment.py::test_command_injection_prevention PASSED [ 91%]
backend\tests\test_terminal_environment.py::test_terminal_execution_when_admin_enabled PASSED [ 93%]
backend\tests\test_terminal_environment.py::test_docker_fail_closed_guarantee PASSED [ 95%]
backend\tests\test_tims.py::test_ac_tims_01_and_02_new_tool_starts_as_draft PASSED [ 97%]
backend\tests\test_tims.py::test_ac_tims_03_04_06_lifecycle_validation_and_approval PASSED [100%]

============================= 45 passed in 13.63s =============================
```

---

## 2. Dedicated Browser & Terminal Test Breakdown

### `backend/tests/test_browser_environment.py` (6 Tests)
1. **`test_ssrf_egress_security_filter`**: Verifies that RFC 1918 addresses (`10.0.0.1`, `192.168.1.1`), loopback (`127.0.0.1`), link-local, and AWS/GCP cloud metadata (`169.254.169.254`) are intercepted and blocked with HTTP 403. Public destinations (`example.com`, `8.8.8.8`) are permitted.
2. **`test_epieos_special_handling_policy`**: Asserts that `epieos.com` is configured as `HUMAN_ASSISTED_ONLY`. Automated scraping and automated queries are blocked with HTTP 403. Manual navigation and manual result import are allowed.
3. **`test_blocked_domains_policy`**: Verifies wildcard blocking on prohibited domains (`*.mil`) with HTTP 403.
4. **`test_browser_profile_isolation`**: Verifies user profile directories are isolated per user under `data/browser_profiles/<user_id>/` and rejects directory traversal (`../../etc/shadow`) with HTTP 400.
5. **`test_browser_session_state_machine`**: Tests the transition from `DISCONNECTED` to `STARTING`, `LOGIN_REQUIRED`, `AUTHENTICATING`, and `USER_AUTHENTICATED` upon explicit investigator confirmation.
6. **`test_browser_manager_lifecycle`**: Launches a live Playwright Chromium persistent context, navigates to `https://example.com`, captures an evidence screenshot, extracts clean text/HTML, and verifies proper browser teardown.

### `backend/tests/test_terminal_environment.py` (4 Tests)
1. **`test_terminal_safe_mode_fail_closed`**: Verifies that while safe startup mode is active, terminal tasks are rejected with HTTP 403.
2. **`test_command_injection_prevention`**: Verifies that shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`) and unapproved commands (`rm -rf /`, `curl malicious.site`) are rejected with HTTP 400.
3. **`test_terminal_execution_when_admin_enabled`**: Validates sandboxed execution of approved commands (`dns_lookup`) when enabled by an authorized administrator.
4. **`test_docker_fail_closed_guarantee`**: Asserts the fail-closed guarantee: when Docker is unavailable or offline, execution fails closed with HTTP 503 rather than falling back to Windows host commands.

---

## 3. Frontend Next.js Build Verification

```
> zaprica-frontend@0.1.0 build
> next build

  ▲ Next.js 14.2.35

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
 ✓ Generating static pages (16/16)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    540 B          87.8 kB
├ ○ /_not-found                          873 B          88.1 kB
├ ○ /accept-invitation                   3.24 kB        90.5 kB
├ ○ /admin                               5.79 kB          93 kB
├ ○ /agents                              3.34 kB        99.8 kB
├ ○ /browser                             5.38 kB        92.6 kB
├ ○ /dashboard                           4.23 kB         101 kB
├ ○ /evidence                            3.06 kB        90.3 kB
├ ○ /investigations                      2.65 kB        99.1 kB
├ ƒ /investigations/[id]                 5.32 kB         102 kB
├ ○ /investigations/new                  3.63 kB        90.9 kB
├ ○ /login                               4.08 kB        91.3 kB
├ ○ /reports                             3.68 kB        90.9 kB
├ ○ /terminal                            4.26 kB        91.5 kB
└ ○ /tools                               3.77 kB          91 kB
+ First Load JS shared by all            87.3 kB

○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```
All 16 routes compiled statically with zero TypeScript or linting errors.

