# ZAPRICA

**AI-assisted, tool-extensible OSINT investigation workspace**

> Status: engineering blueprint / documentation scaffold. This repository currently defines the product and technical contracts; it is not yet a runnable application.

ZAPRICA is designed to accept an investigator's authorized request, plan the work, delegate tasks to browser- and terminal-oriented supervisors, collect and process evidence, correlate findings, and present a traceable report.

## Core operating model

- **Main Head Agent:** central supervisor for intent understanding, scope enforcement, planning, routing, monitoring, consolidation, and reporting.
- **Browser Head Agent:** supervises browser workers that use approved browser capabilities.
- **Terminal Head Agent:** supervises command-line workers operating only through approved, isolated tools.
- **Workers:** perform bounded research or deterministic data-processing tasks and report to their Sub-Head.
- **Tool Intelligence & Management System (TIMS):** lets an administrator onboard, document, test, approve, version, and assign future tools without rewriting the core agents.
- **Evidence pipeline:** preserves raw evidence and creates traceable processed findings.

## Repository layout

```text
my-project/
├── .cursorrules
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_SPEC.yaml
│   ├── SECURITY.md
│   ├── ACCEPTANCE_CRITERIA.md
│   └── DEPLOYMENT.md
├── CONTRIBUTING.md
└── README.md
```

## Recommended technology baseline

| Area | Initial choice |
|---|---|
| Frontend | Next.js App Router, React, TypeScript |
| UI | Tailwind CSS and an accessible component library |
| Backend | Python, FastAPI, Pydantic |
| Agent workflows | LangGraph |
| Durable workflow engine | Temporal later, when justified by long-running/retry requirements |
| Persistence | PostgreSQL, SQLAlchemy 2.x, Alembic |
| Artifact storage | S3-compatible object storage |
| Browser runtime | Playwright in an isolated worker environment |
| Terminal runtime | Rootless Docker/container sandbox with seccomp and restricted egress |
| Tool integration | Internal tool registry first; MCP adapters for compatible tools |
| Cache/ephemeral coordination | Redis only when needed |

Pin exact dependency versions in lockfiles during implementation. This document intentionally avoids claiming that unpinned version ranges are tested together.

## Read the documents in this order

1. [`docs/PRD.md`](docs/PRD.md) — product goals, users, MVP and requirements.
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, data flow, agent protocol and tool onboarding.
3. [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) — persistence model and indexes.
4. [`docs/API_SPEC.yaml`](docs/API_SPEC.yaml) — versioned REST API contract.
5. [`docs/SECURITY.md`](docs/SECURITY.md) — security boundaries and privacy controls.
6. [`docs/ACCEPTANCE_CRITERIA.md`](docs/ACCEPTANCE_CRITERIA.md) — testable Given/When/Then scenarios.
7. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — local, staging and production operations.

## MVP definition

The first vertical slice should support one authorized public website/domain investigation:

1. An authenticated investigator creates an investigation and records its scope.
2. The Main Head creates a small, reviewable plan.
3. The Browser Head dispatches one Playwright worker to an approved, public target.
4. The worker collects bounded page metadata/content and records provenance.
5. Deterministic processors normalize and deduplicate the results without modifying originals.
6. The Browser Head returns a findings package to the Main Head.
7. The Main Head validates the package and generates a report with sources, timestamps, and limitations.
8. The dashboard shows status, findings, evidence references, and the report.

Terminal execution, multiple specialist workers, automatic tool onboarding, graph visualization, and Temporal are later milestones. Tool onboarding should be represented in the data model and API from the beginning, but new tools must remain in draft/review until explicitly approved.

## Safety boundary

ZAPRICA is intended for lawful, authorized, proportionate investigations using public information or assets for which the operator has permission. It must not provide unauthorized access, credential theft, stealth/evasion, malware, exploitation, or indiscriminate sensitive-personal-data collection. Model output is never an authorization decision. Browser and terminal access must be constrained by deterministic policy checks and isolated execution.

## Current state and next step

This is a documentation-first starter. No application source code, Docker Compose file, database migration, or deployment credentials are included yet. The next engineering task is to turn Phase 1 of the PRD into a runnable monorepo scaffold and implement the MVP vertical slice.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) before making changes.
