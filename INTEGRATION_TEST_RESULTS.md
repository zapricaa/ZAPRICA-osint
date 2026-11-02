# ZAPRICA — Integration Test Results & Verification Matrix

**Date**: 2026-11-02  
**Test Runner**: Pytest 9.2.0 (Python 3.13.1, asyncio auto mode) & Next.js 14.2.35  
**Target Environment**: Windows Development Workstation (`hotfix/phase7-remediation`)  
**Overall Result**: **45/45 TESTS PASSED (100%) | FRONTEND BUILD SUCCESS (16/16 ROUTES)**

---

## 1. Backend Automated Pytest Suite Breakdown

```text
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.2.0, pluggy-1.7.0
rootdir: E:\test\ZAPRICA-osint\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, langsmith-0.14.16, asyncio-1.4.1
asyncio: mode=Mode.AUTO, debug=False
collected 45 items

backend\tests\test_ai_brain.py ......                                    [ 13%]
backend\tests\test_auth.py ........                                      [ 31%]
backend\tests\test_browser_environment.py ......                         [ 44%]
backend\tests\test_evidence.py ...                                       [ 51%]
backend\tests\test_investigations.py ....                                [ 60%]
backend\tests\test_main_head.py ..                                       [ 64%]
backend\tests\test_models.py .                                           [ 66%]
backend\tests\test_reports.py .....                                      [ 77%]
backend\tests\test_security.py ....                                      [ 86%]
backend\tests\test_terminal_environment.py ....                          [ 95%]
backend\tests\test_tims.py ..                                            [100%]

============================= 45 passed in 22.91s =============================
```

### Module-by-Module Test Matrix

| Test Suite | Tests | Passed | Failed | Key Invariants Verified |
| :--- | :---: | :---: | :---: | :--- |
| `test_ai_brain.py` | 6 | 6 | 0 | Google Gen AI provider abstraction, model configuration, Pydantic schema validation, tool definitions. |
| `test_auth.py` | 8 | 8 | 0 | Timing-safe bootstrap secret rejection, single-use bootstrap admin creation, argon2id password hashing, MFA verification, invitation flows, session cookie invalidation, suspension revocation. |
| `test_browser_environment.py` | 6 | 6 | 0 | SSRF egress filter blocking private IP ranges / cloud metadata, Epieos `HUMAN_ASSISTED_ONLY` policy, profile isolation outside git, session state machine transitions. |
| `test_evidence.py` | 3 | 3 | 0 | Evidence package ingestion, SHA-256 integrity hashing, immutable storage persistence. |
| `test_investigations.py` | 4 | 4 | 0 | Investigation lifecycle, background task graph execution, status transitions, SSE event streaming. |
| `test_main_head.py` | 2 | 2 | 0 | LangGraph supervisor workflow, sub-head agent delegation, findings package correlation. |
| `test_models.py` | 1 | 1 | 0 | Model registry loading, official model identifier validation (`gemini-2.0-flash`). |
| `test_reports.py` | 5 | 5 | 0 | Final investigation report synthesis, PDF/HTML generation, audit log compliance. |
| `test_security.py` | 4 | 4 | 0 | Safe startup defaults, terminal execution disabled by default, policy enforcement guards. |
| `test_terminal_environment.py` | 4 | 4 | 0 | Container command allowlisting, argument injection prevention, strict fail-closed guarantee (zero host fallback). |
| `test_tims.py` | 2 | 2 | 0 | Tool draft registration, isolated sandbox validation, human administrator approval and publishing. |

---

## 2. Frontend Production Build Verification

```text
> zaprica-frontend@0.1.0 build
> next build

  ▲ Next.js 14.2.35

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/16) ...
   Generating static pages (4/16) 
   Generating static pages (8/16) 
   Generating static pages (12/16) 
 ✓ Generating static pages (16/16)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    540 B          87.8 kB
├ ○ /_not-found                          873 B          88.1 kB
├ ○ /accept-invitation                   3.24 kB        90.5 kB
├ ○ /admin                               5.79 kB          93 kB
├ ○ /agents                              3.33 kB        99.8 kB
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

- All 16 pages compiled without warnings or syntax errors.
- Internal Docker rewrite proxy configured via `INTERNAL_API_URL` to route seamlessly to the backend container.

