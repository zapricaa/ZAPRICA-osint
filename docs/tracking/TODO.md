# ZAPRICA Master Implementation TODO

## Phase 0: Inspection & Technical Planning [COMPLETED]
- [x] Read all documentation and rules.
- [x] Identify technical gaps and document decisions (`docs/TECHNICAL_DECISIONS.md`).
- [x] Create project progress trackers (`docs/IMPLEMENTATION_STATUS.md`, `docs/DEVELOPMENT_LOG.md`, `docs/TODO.md`, `WORK_LOG.md`, `SYSTEM_ARCHITECTURE_FLOW.md`).

## Phase 1: Project Setup & Foundation [COMPLETED]
- [x] Create root `.env.example`.
- [x] Scaffold `backend/` directory with `pyproject.toml`, requirements, venv, and dependencies.
- [x] Scaffold `frontend/` directory with Next.js 14, Tailwind CSS, TypeScript, and UI component foundations.
- [x] Verify backend importability and baseline test runner.

## Phase 2: Database Schema & Core Persistence [COMPLETED]
- [x] Implement SQLAlchemy 2.0 models for all tables in `DATABASE_SCHEMA.md`:
  - `workspaces`, `workspace_memberships`
  - `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `user_tool_permissions`
  - `sessions`, `login_attempts`, `invitations`
  - `investigations`, `investigation_scopes`
  - `tasks`, `agent_runs`, `tool_runs`
  - `tools`, `tool_versions`, `agent_tool_assignments`
  - `evidence_artifacts`, `findings`, `finding_sources`
  - `entities`, `entity_relationships`
  - `reports`, `approval_requests`, `audit_events`
- [x] Configure Alembic for database migrations (`alembic upgrade head`).
- [x] Implement async database engine and GUID type decorators.
- [x] Unit tests passing for all models and relations.

## Phase 3: Invite-Only Authentication, RBAC & Sessions [COMPLETED]
- [x] Disable public registration (no anonymous signup).
- [x] Implement one-time bootstrap endpoint for first SUPER_ADMIN.
- [x] Implement Argon2id password hashing via `pwdlib` with bcrypt fallback.
- [x] Implement TOTP MFA via `pyotp`.
- [x] Implement session management with `sessions` table, SHA-256 token hashing, and HttpOnly cookies.
- [x] Implement brute-force protection with `login_attempts` logging and lockouts.
- [x] Implement Administrator User & Invitation Management endpoints.
- [x] Automated tests passing in `tests/test_auth.py`.

## Phase 4: Core REST API & Event Streaming [COMPLETED]
- [x] Implement `/v1/investigations` CRUD endpoints matching `API_SPEC.yaml`.
- [x] Implement investigation lifecycle controls (`/start`, `/pause`, `/resume`, `/cancel`).
- [x] Implement `/v1/investigations/{id}/tasks`, `/findings`, `/evidence`, `/reports`.
- [x] Implement Server-Sent Events (SSE) `/v1/investigations/{id}/events`.
- [x] Standardize API error handling with unified `ErrorResponse` schema.
- [x] Integration tests passing in `tests/test_investigations.py`.

## Phase 5: Evidence Storage & Deterministic Processors [COMPLETED]
- [x] Implement pluggable evidence storage (`LocalStorageBackend`, `S3StorageBackend`).
- [x] Enforce SHA-256 hash calculation and immutability checks on all stored evidence.
- [x] Implement deterministic data cleaning, normalization, duplicate removal, and classification workers.
- [x] Unit tests passing for AC-EVD-01, AC-EVD-02, AC-EVD-03, AC-EVD-04.

## Phase 6: Google Gemini AI Brain & Main Head Agent [COMPLETED]
- [x] Integrate official `google-genai` >= 2.3.0 SDK.
- [x] Implement configurable Model Registry (`gemini-3.8-flash`, `gemini-3.5-flash-lite`).
- [x] Implement structured Pydantic reasoning schemas.
- [x] Implement prompt injection defense with `<untrusted_data>` segregation.
- [x] Implement LangGraph workflow graph in `MainHeadGraphRunner`:
  - `parse_request`
  - `scope_gate`
  - `plan`
  - `decompose`
  - `route`
  - `consolidate`
  - `report`
- [x] Automated tests passing in `tests/test_ai_brain.py` and `tests/test_main_head.py`.

## Phase 7: Browser Head Agent & Playwright Workers [COMPLETED]
- [x] Implement `BrowserHeadAgent` supervisor.
- [x] Implement SSRF egress filter blocking private IPs, loopback, and cloud metadata.
- [x] Implement Playwright metadata & content extraction worker.

## Phase 8: Terminal Head Agent & Sandboxed CLI Adapters [COMPLETED]
- [x] Implement `TerminalHeadAgent` supervisor.
- [x] Implement `ToolGateway` rejecting arbitrary shell commands (AC-SEC-01).
- [x] Implement fixed adapters (`dns_lookup`, `whois_lookup`) with argument schema validation.

## Phase 9: TIMS (Tool Intelligence & Management System) [COMPLETED]
- [x] Implement tool manifest registration and draft status.
- [x] Implement automated playbook generation from documentation.
- [x] Implement isolated validation environment with non-root checks.
- [x] Implement separate administrator approval gate and publishing.
- [x] Implement agent capability discovery and emergency revocation kill-switch.
- [x] Automated tests passing in `tests/test_tims.py`.

## Phase 10: Safe Application Startup Mode [COMPLETED]
- [x] Implement `ZAPRICA_SAFE_MODE=true` and `TERMINAL_EXECUTION_ENABLED=false` by default.
- [x] Implement `SafeModeController` tracking agent states (IDLE) and workers (DISABLED).
- [x] Read-only DB health check on startup.
- [x] Admin override endpoints to enable terminal capabilities with audit logging.

## Phase 11: Frontend Dashboard & Interactive Views [COMPLETED]
- [x] Connect Next.js frontend to backend API and SSE.
- [x] Build `/login` (username/email, password, MFA challenge, one-time super admin bootstrap).
- [x] Build `/accept-invitation` (token acceptance, password setup).
- [x] Build `/dashboard` (operational metrics, safe mode badge, agent fleet status, recent missions).
- [x] Build `/investigations` (workspace catalogue) and `/investigations/new` (target wizard with SSRF scope boundaries).
- [x] Build `/investigations/[id]` (live workspace, LangGraph stage visualizer, tasks, evidence, SSE event feed).
- [x] Build `/evidence` (SHA-256 provenance explorer, copy hash, media filters).
- [x] Build `/tools` (TIMS tool lifecycle: draft, approve, publish to agents).
- [x] Build `/reports` (intelligence synthesis with observed facts vs inferences separation).
- [x] Build `/agents` (agent fleet supervision cards).
- [x] Build `/admin` (user management, invitation generator, sessions, login attempts audit, safe mode toggle).
- [x] Type checking and static production build verified (`npm run build`).

## Phase 12: Deployment & Packaging [COMPLETED]
- [x] Multi-stage `backend/Dockerfile` with non-root user and Playwright chromium.
- [x] Multi-stage `frontend/Dockerfile` with non-root user and production server.
- [x] `docker-compose.yml` for unified local stack with PostgreSQL 16 Alpine and healthchecks.

## Phase 13: Dedicated Browser & Terminal Environments Upgrade [COMPLETED]
- [x] Database migrations (`ed0d07b96175`): `browser_profiles`, `browser_sessions`, `terminal_environments`, `terminal_tasks`, `terminal_execution_logs`, `tool_execution_policies`, `website_automation_policies`.
- [x] Browser profile isolation outside git with path traversal checks.
- [x] Human login protocol with explicit `USER_AUTHENTICATED` investigator confirmation.
- [x] Epieos special handling (`HUMAN_ASSISTED_ONLY`, manual access and manual result import).
- [x] Website automation policies (`AUTOMATED_ALLOWED`, `HUMAN_ASSISTED_ONLY`, `API_ONLY`, `BLOCKED`).
- [x] Hardened Docker container sandbox execution with read-only rootfs, non-root user, tmpfs `/workspace`, dropped capabilities, and strict fail-closed guarantee (no host execution fallback).
- [x] Allowlisted command specs with Pydantic validation & injection rejection.
- [x] Dedicated terminal workers (`CliOsintWorker`, `NetworkIntelligenceWorker`, `MetadataAnalysisWorker`, `FileDocumentProcessingWorker`) and `SortingAndIndexingWorker`.
- [x] Enriched `TaskEnvelope` contracts with scope, permitted domains/tools, execution mode.
- [x] Interactive `/browser` and `/terminal` workspaces in Next.js frontend with live telemetry.
- [x] 45/45 automated pytest tests passing cleanly.
- [x] 16/16 frontend routes statically compiled and verified via `npm run build`.
