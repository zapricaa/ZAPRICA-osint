# ZAPRICA Technical Decisions Record (TDR)

## TDR-001: Architecture & Repository Structure (Modular Monolith)
- **Status:** Approved
- **Context:** The project requires a frontend dashboard, a backend API, agent workflows (Main Head, Browser Head, Terminal Head), worker execution sandboxes, and TIMS (Tool Intelligence & Management System).
- **Decision:** Adopt a modular monolith structured into `backend/` and `frontend/`:
  - `backend/app/`: FastAPI application split into domain services (`auth`, `investigations`, `agents`, `tools`, `evidence`, `reports`, `audit`, `events`), database models, repositories, and execution gateways.
  - `frontend/`: Next.js 14+ App Router with TypeScript, Tailwind CSS, and shadcn-style component primitives.
- **Consequences:** Low operational complexity, straightforward local development, easy integration testing, clean separation of concerns without premature microservice overhead.

## TDR-002: Dual Database Engine Support (PostgreSQL & SQLite for Hermetic Testing)
- **Status:** Approved
- **Context:** The system of record specified in `DATABASE_SCHEMA.md` is PostgreSQL with UUIDs, JSONB, and foreign keys. Fast local automated unit/integration tests must run reliably across developer environments (including Windows without requiring Docker Postgres pre-installed).
- **Decision:** Design SQLAlchemy 2.0 models using dialect-agnostic constructs (e.g. `TypeDecorator` or `GUID` type that maps to native `postgresql.UUID` in Postgres and `CHAR(36)` in SQLite; JSON type that maps to `JSONB` in Postgres and `JSON` in SQLite). Production and staging will use PostgreSQL. Alembic will manage production migrations.
- **Consequences:** Developers can run `pytest` hermetically in seconds anywhere, while production runs on robust PostgreSQL with full JSONB and index support.

## TDR-003: Evidence Storage Abstraction (S3 & Local File Storage)
- **Status:** Approved
- **Context:** Raw evidence must be immutable, verified with SHA-256 hashes, and stored separately from derived findings. Production uses S3-compatible storage. Local dev should not fail if MinIO is not running.
- **Decision:** Implement an `EvidenceStorage` interface with:
  1. `LocalStorageBackend`: writes to a configurable directory (e.g., `data/evidence/`) with SHA-256 validation.
  2. `S3StorageBackend`: connects to S3/MinIO via boto3.
- **Consequences:** Smooth local development while adhering strictly to the immutability and provenance contracts defined in `docs/PRD.md` and `docs/SECURITY.md`.

## TDR-004: Configurable LLM Provider Interface & Prompt Injection Defense
- **Status:** Approved
- **Context:** `docs/ARCHITECTURE.md` and `.cursorrules` mandate that model providers remain behind an adapter interface and never hardcode API keys or model names. Furthermore, web pages and untrusted evidence must not alter agent instructions (prompt injection mitigation).
- **Decision:** Build an `LLMProvider` abstraction layer:
  - Supported providers: `MockLLMProvider` (deterministic, test fixtures), `GeminiProvider`, `OpenAICompatibleProvider`.
  - Structured output parsing using Pydantic schemas.
  - Clear demarcations in prompts separating System instructions, Investigator Objectives, Retrieved Tool Playbooks, and Untrusted External Evidence (wrapped in `<untrusted_content>` tags with explicit parsing instructions).
- **Consequences:** Reproducible, zero-cost CI testing; plug-and-play production LLM models; defense-in-depth against prompt injection.

## TDR-005: Sandboxed Tool Execution & SSRF Egress Filter
- **Status:** Approved
- **Context:** Browser automation (Playwright) and CLI tools must be prevented from accessing internal infrastructure, loopback (`127.0.0.1`), RFC1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.169.254`), and cloud metadata services.
- **Decision:**
  - Browser Worker: Implement navigation URL validation and IP resolution hooks that verify DNS records before Playwright navigates, and reject non-allowlisted schemes or private IP resolutions.
  - Terminal Worker: Implement an approved command adapter registry with strictly typed Pydantic parameter schemas, executing fixed binaries via `subprocess.run(..., shell=False)` without shell interpolation, enforcing resource limits and execution timeouts.
- **Consequences:** Robust security compliance meeting `docs/SECURITY.md` and `docs/ACCEPTANCE_CRITERIA.md`.

## TDR-006: Real-Time Event Delivery via Server-Sent Events (SSE)
- **Status:** Approved
- **Context:** The frontend needs live investigation progress, agent status, and worker logs without aggressive polling.
- **Decision:** Implement FastAPI SSE streaming at `/v1/investigations/{investigationId}/events` backed by an in-memory or Redis-backed PubSub event bus.
- **Consequences:** Satisfies `docs/API_SPEC.yaml` `/events` endpoint, provides responsive UI updates, and eliminates polling overhead.

---

## TDR-007: Official Google Gen AI SDK (`google-genai`) & Structured Pydantic Reasoning
- **Context:** System requires advanced AI reasoning across Main Head, Browser Head, and Terminal Head.
- **Decision:** Adopt official `google-genai` >= 2.3.0 SDK using `genai.Client()`. Use `gemini-3.8-flash` for high-fidelity supervisor reasoning and `gemini-3.5-flash-lite` for high-throughput sub-heads. Disallow deprecated legacy SDKs (`google-generativeai`) and older model families.
- **Consequences:** Provides native `response_schema` enforcement, prompt injection `<untrusted_data>` segregation, rate-limit backoff, and model role configurability.

---

## TDR-008: Invite-Only Authentication & Session Management
- **Context:** ZAPRICA must prevent public signups and anonymous accounts, enforcing administrative onboarding and MFA.
- **Decision:** Implement zero public registration. Super admin is bootstrapped once via `/v1/auth/bootstrap`. Subsequent users are provisioned directly or onboarded via single-use cryptographically hashed invitation links (`invitations` table). Passwords hashed using Argon2id via `pwdlib`. MFA implemented using TOTP via `pyotp`. Sessions tracked in `sessions` table and delivered via HttpOnly cookies.
- **Consequences:** Fulfills invite-only platform security, eliminates rogue self-registration, and provides immediate session revocation upon suspension.

---

## TDR-009: Safe Application Startup Mode (Default-Disabled Terminal Execution)
- **Context:** Uncontrolled agent execution on Windows host risks arbitrary code execution or unapproved active OSINT touches.
- **Decision:** Enable Safe Startup Mode by default (`ZAPRICA_SAFE_MODE=true`, `TERMINAL_EXECUTION_ENABLED=false`). Agents start in `IDLE` state; workers start `DISABLED`. Outbound CLI tool execution fails closed unless a Super Admin explicitly enables execution capabilities via `/v1/admin/safe-mode/terminal-execution`.
- **Consequences:** Host safety is guaranteed out-of-the-box, background tasks cannot fire unprompted on boot, and administrators hold total control over tool capabilities.
