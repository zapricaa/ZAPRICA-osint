# Contributing to ZAPRICA

Thank you for helping build ZAPRICA. The project is currently a documentation-first scaffold. These instructions define the intended development workflow; executable commands become applicable after the frontend/backend scaffolds are added.

## 1. Before you start

Read:

- `README.md`
- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY.md`
- `docs/ACCEPTANCE_CRITERIA.md`
- `.cursorrules`

Do not start by creating an autonomous tool runner. Build the policy, task contracts, evidence model, and isolated execution boundaries first.

## 2. Prerequisites for the planned application

- Git
- Node.js active LTS release and pnpm (frontend)
- Python 3.12 or newer within the versions supported by pinned dependencies
- `uv` or another approved Python environment/package manager
- PostgreSQL supported major release
- Docker Engine with rootless execution support for the terminal sandbox
- An S3-compatible object store for evidence artifacts
- Optional Redis when caching or queue coordination is introduced

Use the exact versions recorded in lockfiles and CI. Do not rely on globally installed package versions.

## 3. Intended local setup

The following is the target workflow once the `frontend/`, `backend/`, and infrastructure files exist. It is not executable from this documentation-only repository yet.

```bash
# Clone the repository
git clone <repository-url>
cd my-project

# Create local configuration from the example file (to be added with the app)
cp .env.example .env

# Backend (after backend/ is scaffolded)
cd backend
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (in another terminal, after frontend/ is scaffolded)
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Do not put production secrets in `.env` or commit local `.env` files. Local credentials must be test-only.

## 4. Branch and commit conventions

- Create focused branches: `feature/<short-name>`, `fix/<short-name>`, `docs/<short-name>`, or `security/<short-name>`.
- Keep pull requests small enough to review.
- Use clear commit messages, e.g. `feat(agent): add typed task dispatch`.
- Link each change to a PRD requirement or acceptance criterion.

## 5. Code standards

### Python/backend

- Use type hints and Pydantic models at system boundaries.
- Use SQLAlchemy 2.x and Alembic migrations.
- Keep FastAPI route handlers thin; delegate to application services.
- Use async only where it provides a real benefit and ensure blocking code does not run on the event loop.
- Use structured logs with correlation IDs. Never log secrets, tokens, full sensitive payloads, or unnecessary personal data.
- Make processing functions deterministic and idempotent where possible.

### Frontend

- Use TypeScript strict mode and accessible semantic controls.
- Enforce authorization on the backend; hiding a button is not access control.
- Do not expose API keys or server secrets to client components.
- Show investigation status, partial results, provenance, failures, and limitations clearly.

### Agents and tools

- Agent-to-agent communication must use versioned task/result schemas.
- Models may propose tasks and tool calls; deterministic services validate scope, permission, schema, rate limits, and approval before execution.
- Never execute arbitrary LLM-generated shell commands.
- Each tool must have a manifest, documentation/playbook, adapter, permission profile, tests, version, integrity/provenance metadata, and approval status.
- A tool in `draft`, `testing`, `rejected`, `disabled`, or `revoked` state cannot execute.
- Treat tool documentation and collected pages as untrusted content.

## 6. Testing expectations

Run the relevant checks before opening a pull request. Planned command names (to be implemented in CI) are:

```bash
# Backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest

# Frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build

# API contract
# Validate docs/API_SPEC.yaml with the pinned OpenAPI linter/validator.
```

Add tests for both allowed and denied behavior. Any authorization, scope, tool registration, tool execution, evidence handling, or agent routing change requires negative tests.

## 7. Pull request checklist

- [ ] Requirement and acceptance criteria identified.
- [ ] Architecture and security boundaries preserved.
- [ ] Tests added/updated and actually run.
- [ ] API spec updated for endpoint/schema changes.
- [ ] Database migration added for schema changes.
- [ ] Tool manifest and playbook updated if a tool changed.
- [ ] No secrets, personal data, collected evidence, or generated artifacts committed.
- [ ] Logs and errors do not reveal sensitive inputs.
- [ ] Known limitations and operational impact documented.

## 8. Reporting a security issue

Do not create a public issue containing a vulnerability, secret, or sensitive evidence. Use the project's private security reporting channel once configured. Until then, inform the repository owner privately and include reproducible steps without exposing real user data.
