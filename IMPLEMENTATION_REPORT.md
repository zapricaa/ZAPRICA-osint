# ZAPRICA — Dedicated Browser & Terminal Environments Implementation Report

**Date**: 2026-11-02  
**System**: ZAPRICA Multi-Agent OSINT Investigation Platform  
**Status**: UPGRADE COMPLETED & VERIFIED  

---

## 1. Executive Summary

This engineering upgrade implements dedicated, isolated operational environments for the **Browser Head Agent** and the **Terminal Head Agent**, while preserving the existing architectural foundations, safe startup invariants, and the 3-tier hierarchy governed by the **Main Head AI Agent** (powered by Google Gemini and LangGraph).

Neither Sub-Head agent relies on personal browser instances or unrestricted Windows host terminal execution. Both environments are independently managed, observable, permission-controlled, and seamlessly connected to the LangGraph orchestration pipeline.

---

## 2. Key Accomplishments & Deliverables

### 2.1 Dedicated Browser Environment
- **Persistent Playwright Engine**: Replaced lightweight HTTP fetching with a robust Playwright Chromium persistent context engine (`BrowserManager`), enabling true web reconnaissance, visual screenshots, and DOM inspection.
- **Per-User Profile Isolation**: User profiles are stored in `data/browser_profiles/<user_id>/` outside version control. Path traversal attempts (`..`, `/`, `\`) are strictly intercepted and rejected with HTTP 400 Bad Request.
- **Human-in-the-Loop Authentication**: Added full state machine supporting `LOGIN_REQUIRED`, `AUTHENTICATING`, and `USER_AUTHENTICATED`. Investigators take manual control of interactive logins, and automation cannot resume without explicit investigator confirmation (`POST /api/v1/browser/sessions/{session_id}/confirm-authentication`).
- **Website Automation Policy**: `BrowserPolicyEngine` evaluates target domains against 4 explicit policies:
  1. `AUTOMATED_ALLOWED`: Automated queries and extractions permitted within scope.
  2. `HUMAN_ASSISTED_ONLY`: Operator conducts manual lookup; agent extracts/imports results only.
  3. `API_ONLY`: Web automation blocked; queries must pass via official API adapters.
  4. `BLOCKED`: Target strictly prohibited (e.g., military domains, dark web, unapproved destinations).
- **Epieos Special Invariant**: `epieos.com` is strictly enforced as `HUMAN_ASSISTED_ONLY`. Automated scraping and automated queries are blocked by immutable backend policy. Manual user access and manual result import (`/import-manual-result`) are fully supported.
- **SSRF & Egress Security**: `BrowserSecurityValidator` executes DNS pre-resolution and blocks all RFC 1918 private IPs, loopback, link-local, and cloud metadata endpoints (`169.254.169.254`) across all navigational hops and redirects.

### 2.2 Dedicated Terminal Sandbox Environment
- **Container Sandbox Isolation**: Implemented `DockerSandboxManager` enforcing:
  - Immutable read-only root filesystem (`--read-only`).
  - In-memory volatile workspace (`--tmpfs /workspace:rw,noexec,nosuid,size=64m`).
  - Unprivileged non-root user (`--user 10001:10001`).
  - Dropped Linux capabilities (`--cap-drop=ALL`).
  - Privilege restriction (`--security-opt=no-new-privileges`).
  - Resource caps (`--pids-limit=64`, `-m 256m`, `--cpus 0.5`).
- **Strict Fail-Closed Guarantee**: Agent commands are NEVER executed on the Windows host. If Docker daemon is unavailable, the application immediately rejects execution with HTTP 503 Service Unavailable.
- **Command Allowlist & Injection Defense**: `TerminalExecutionPolicyValidator` validates commands against strict specifications (`dns_lookup`, `whois_lookup`, `metadata_extractor`, `subdomain_enum`, `cert_inspector`). Semicolons, pipes, redirects, backticks, and subshells are strictly rejected.
- **Dedicated Terminal Workers**: Implemented `CliOsintWorker`, `NetworkIntelligenceWorker`, `MetadataAnalysisWorker`, and `FileDocumentProcessingWorker`.
- **Dedicated Processing Workers**: Implemented `SortingAndIndexingWorker`, alongside `DataCleaningWorker` and `DuplicateDetectionWorker`.

### 2.3 Main Head Integration & Contracts
- **Enriched TaskEnvelope**: All tasks dispatched by Main Head now include `initiating_user_id`, `parent_agent`, `authorized_scope`, `permitted_domains`, `permitted_tools`, `execution_mode`, `approval_requirements`, and `timeout_seconds`.
- **Findings Packages**: Both Sub-Heads return typed, verified `FindingsPackage` instances with cryptographic SHA-256 evidence links back to the Main Head.

### 2.4 Database Schema & Migrations
- **Alembic Revision**: `ed0d07b96175` applied cleanly to the database.
- **New Tables**: `browser_profiles`, `browser_sessions`, `browser_session_events`, `browser_tasks`, `terminal_environments`, `terminal_sessions`, `terminal_tasks`, `terminal_execution_logs`, `website_automation_policies`, `tool_execution_policies`, `human_approvals`.

### 2.5 Frontend Control Centers
- **/browser**: Interactive Browser Control Center supporting session creation, live URL navigation, real-time status badges, proof screenshot capture, human authentication confirmation banner, and manual Epieos result import modal.
- **/terminal**: Terminal Control Center with sandbox status banner, approved command selector, parameter form, dispatch button, and real-time ANSI terminal console log viewer.
- **/agents**: Enhanced Multi-Agent Fleet Supervision page with direct links to Browser and Terminal workspaces and live telemetry.
- **Sidebar**: Integrated global navigation links for Browser Workspace (`/browser`) and Terminal Workspace (`/terminal`).

---

## 3. Verification & Compliance Matrix

| Requirement | Implementation Component | Test Suite File | Status |
| :--- | :--- | :--- | :--- |
| **Browser Isolation** | `BrowserProfileManager` | `test_browser_environment.py` | PASSED |
| **Human Login Confirmation** | `BrowserSessionManager` | `test_browser_environment.py` | PASSED |
| **Website Automation Policy** | `BrowserPolicyEngine` | `test_browser_environment.py` | PASSED |
| **Epieos Special Invariant** | `BrowserPolicyEngine` + `PlaywrightBrowserWorker` | `test_browser_environment.py` | PASSED |
| **SSRF / Egress Defense** | `BrowserSecurityValidator` | `test_browser_environment.py` | PASSED |
| **Terminal Docker Sandbox** | `DockerSandboxManager` | `test_terminal_environment.py` | PASSED |
| **Terminal Fail-Closed Guard** | `DockerSandboxManager` + `TerminalManager` | `test_terminal_environment.py` | PASSED |
| **Command Injection Defense** | `TerminalExecutionPolicyValidator` | `test_terminal_environment.py` | PASSED |
| **Tool Execution Policies** | `backend/app/api/v1/tools.py` | `test_terminal_environment.py` | PASSED |
| **Frontend Static Compilation**| Next.js App Router (16 routes) | `npm run build` | PASSED (0 Errors) |
| **Full Test Suite** | 45 pytest tests across all subsystems | `pytest backend/tests` | PASSED (45/45) |
