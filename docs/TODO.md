# ZAPRICA Master Implementation TODO

## Phase 0: Inspection & Technical Planning [COMPLETED]
- [x] Read all documentation and rules.
- [x] Identify technical gaps and document decisions (`docs/TECHNICAL_DECISIONS.md`).
- [x] Create project progress trackers (`docs/IMPLEMENTATION_STATUS.md`, `docs/DEVELOPMENT_LOG.md`, `docs/TODO.md`).

## Phase 1: Project Setup & Foundation [IN PROGRESS]
- [ ] Create root `.env.example`.
- [ ] Scaffold `backend/` directory with `pyproject.toml`, dependencies, and directory structure.
- [ ] Scaffold `frontend/` directory with Next.js, Tailwind CSS, TypeScript, and UI component foundations.
- [ ] Verify backend importability and baseline test runner.

## Phase 2: Database Schema & Core Persistence
- [ ] Implement SQLAlchemy 2.0 models for all tables in `DATABASE_SCHEMA.md`:
  - `workspaces`, `users`, `workspace_memberships`
  - `investigations`, `investigation_scopes`
  - `tasks`, `agent_runs`, `tool_runs`
  - `tools`, `tool_versions`, `agent_tool_assignments`
  - `evidence_artifacts`, `findings`, `finding_sources`
  - `entities`, `entity_relationships`
  - `reports`, `approval_requests`, `audit_events`
- [ ] Configure Alembic for database migrations.
- [ ] Implement database session management and repository pattern.
- [ ] Write unit tests for schema constraints and foreign key relationships.

## Phase 3: Authentication, RBAC & Workspace Scoping
- [ ] Implement password hashing and JWT token issuance/verification.
- [ ] Implement user registration, login, and `/v1/me` endpoint.
- [ ] Implement workspace membership validation and role hierarchy (`admin`, `investigator`, `reviewer`, `viewer`).
- [ ] Implement FastAPI dependency injection for `CurrentUser`, `CurrentWorkspace`, and role checks.
- [ ] Write automated tests for AC-AUTH-01, AC-AUTH-02, AC-AUTH-03, AC-AUTH-04.

## Phase 4: Core REST API & Event Streaming
- [ ] Implement `/v1/investigations` CRUD endpoints matching `API_SPEC.yaml`.
- [ ] Implement investigation lifecycle controls (`/start`, `/pause`, `/resume`, `/cancel`).
- [ ] Implement `/v1/investigations/{id}/tasks`, `/findings`, `/evidence`, `/reports`.
- [ ] Implement Server-Sent Events (SSE) `/v1/investigations/{id}/events`.
- [ ] Standardize API error handling with unified `ErrorResponse` schema.
- [ ] Write integration tests for API endpoints.

## Phase 5: Evidence Storage & Deterministic Processors
- [ ] Implement pluggable evidence storage (`LocalStorageBackend`, `S3StorageBackend`).
- [ ] Enforce SHA-256 hash calculation and immutability checks on all stored evidence.
- [ ] Implement deterministic data cleaning, normalization, duplicate removal, and classification workers.
- [ ] Write unit tests for AC-EVD-01, AC-EVD-02, AC-EVD-03, AC-EVD-04.

## Phase 6: Main Head AI Agent (LangGraph Orchestration)
- [ ] Define Pydantic models for Agent State, Intent, Plans, Tasks, Findings Packages.
- [ ] Implement LangGraph workflow graph:
  - `parse_request`
  - `scope_gate`
  - `plan`
  - `decompose`
  - `route`
  - `monitor`
  - `consolidate`
  - `evaluate_gaps`
  - `replan`
  - `report`
- [ ] Implement LLM provider abstraction with deterministic test runner.
- [ ] Enforce strict scope check preventing model from expanding target boundaries.
- [ ] Write automated tests for AC-MAIN-01, AC-MAIN-02, AC-MAIN-03, AC-MAIN-04.

## Phase 7: Browser Head Agent & Playwright Workers
- [ ] Implement Browser Head agent logic and task dispatch.
- [ ] Implement isolated Playwright browser contexts.
- [ ] Implement SSRF defense: DNS resolution check, blocking private/loopback/cloud metadata IPs.
- [ ] Implement Web Page Metadata & Content Extraction Worker.
- [ ] Build findings packaging and provenance tracking back to Browser Head.
- [ ] Write tests for AC-AGENT-01, AC-AGENT-02, AC-SEC-02.

## Phase 8: Terminal Head Agent & Sandboxed CLI Adapters
- [ ] Implement Terminal Head agent supervisor.
- [ ] Implement Tool Execution Gateway with argument schema validation (prevent arbitrary shell commands).
- [ ] Implement initial benign CLI adapters (e.g. `whois_lookup`, `dns_lookup`, `ping_check`, `metadata_extract`).
- [ ] Enforce resource limits, execution timeouts, non-zero exit handling.
- [ ] Write tests for AC-SEC-01, AC-SEC-04.

## Phase 9: TIMS (Tool Intelligence & Management System)
- [ ] Implement tool registration and manifest management.
- [ ] Implement playbook markdown generation & documentation storage.
- [ ] Implement isolated tool test runner (`/validate`).
- [ ] Implement admin approval workflow (`/approve`, `/publish`, `/disable`, `/activate-version`).
- [ ] Implement agent capability discovery filtering by agent class and approval status.
- [ ] Write tests for AC-TIMS-01 through AC-TIMS-07.

## Phase 10: Findings Correlation & Report Generation
- [ ] Implement cross-source duplicate detection and conflict highlighting.
- [ ] Implement Report Service generating structured findings summaries with provenance links.
- [ ] Implement JSON, CSV, and Markdown export formats.
- [ ] Write tests for AC-REPORT-01 through AC-REPORT-04.

## Phase 11: Frontend Dashboard & Investigation Workspace
- [ ] Build responsive dark-themed UI with Tailwind CSS and accessible components:
  - Authentication (Login / Register)
  - Dashboard (Active, Completed, Failed investigations, Stats)
  - New Investigation with Scope configuration
  - Investigation Workspace with Live Agent Graph, Task List, Findings Stream
  - Evidence Explorer with raw/processed views and provenance modal
  - Tool Manager (Admin catalog, version inspector, approval actions)
  - Investigation Reports viewer with export actions
- [ ] Connect frontend to backend REST API and SSE event stream.

## Phase 12: Security Hardening & Acceptance Verification
- [ ] Run full test suite covering all Acceptance Criteria (AC-AUTH, AC-INV, AC-MAIN, AC-AGENT, AC-EVD, AC-TIMS, AC-SEC, AC-REPORT).
- [ ] Perform prompt injection resilience test.
- [ ] Verify audit log integrity.

## Phase 13: Deployment Preparation
- [ ] Create Dockerfiles for Backend, Frontend, and Worker execution.
- [ ] Create `docker-compose.yml` for unified local/staging deployment.
- [ ] Document production deployment checklist and environment variables.
