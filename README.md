# ZAPRICA

**AI-Assisted, Tool-Extensible OSINT Investigation Workspace**

ZAPRICA is an enterprise-grade open-source intelligence platform featuring a 3-tier multi-agent hierarchy (LangGraph), Google Gemini AI Brain (`google-genai`), invite-only authentication with RBAC, safe startup mode, dedicated Playwright browser automation, and hardened Docker container execution sandboxes.

---

## Clean Repository Structure

All runtime application code, orchestration assets, and non-application documentation are strictly segregated:

```text
ZAPRICA-osint/
├── backend/            # FastAPI Python backend (Agents, LangGraph, API v1, Services, Tests)
├── frontend/           # Next.js 14 React frontend (Dashboard, Investigation, Browser & Terminal UI)
├── docker/             # Isolated Docker container sandbox definitions
├── data/               # Persistent runtime evidence storage & browser profiles (gitignored)
├── docs/               # ALL non-application files (Architecture, Reports, Specs, Tracking)
│   ├── architecture/   # 3-Tier Multi-Agent architecture, schemas, and environment specs
│   ├── reports/        # Independent audits, remediation reports, and test verification logs
│   ├── specifications/ # PRD, acceptance criteria, security threat model, and deployment
│   ├── tracking/       # Development logs, implementation status, and ADR decisions
│   └── README.md       # Master documentation index and guide
├── .cursorrules        # Agent and IDE development guidelines
├── .env                # Local environment configuration
├── .gitignore          # Version control ignore rules
├── docker-compose.yml  # Multi-service production stack orchestration
├── README.md           # Root overview and quickstart guide
└── zaprica.db          # Local SQLite development database
```

---

## 3-Tier Multi-Agent Hierarchy

```
                            +-----------------------------------+
                            |         HUMAN INVESTIGATOR        |
                            +-----------------+-----------------+
                                              |
                                              | (Authenticated Request)
                                              v
+-----------------------------------------------------------------------------------------------+
|                                    MAIN HEAD AI AGENT                                         |
|                  (Strategic Planning, LangGraph Workflow, Findings Correlation)               |
+-------------------------------+-------------------------------+-------------------------------+
                                |                               |
        (TaskEnvelope: Scope,   |                               |  (TaskEnvelope: Scope,
         Permitted Domains,     |                               |   Permitted Tools,
         Execution Mode)        |                               |   Execution Mode)
                                v                               v
+-----------------------------------------------+   +-------------------------------------------+
|               BROWSER HEAD AGENT              |   |            TERMINAL HEAD AGENT            |
|       (Dedicated Browser Environment)         |   |       (Dedicated Sandbox Environment)     |
+-----------------------+-----------------------+   +---------------------+---------------------+
                        |                                                 |
         +--------------v--------------+                   +--------------v--------------+
         |    BROWSER POLICY ENGINE    |                   |  TERMINAL EXECUTION POLICY  |
         |  (AUTOMATED, HUMAN_ASSISTED)|                   |  (Allowlist Specs, Pydantic)|
         +--------------+--------------+                   +--------------+--------------+
                        |                                                 |
         +--------------v--------------+                   +--------------v--------------+
         |       BROWSER MANAGER       |                   |    DOCKER SANDBOX MANAGER   |
         | (Playwright Chromium Engine)|                   | (Isolated Non-Root Sandbox) |
         +-----------------------------+                   +-----------------------------+
```

---

## Quickstart (Local Development)

### 1. Prerequisites
- Python 3.12+ / 3.13
- Node.js 18+ & npm
- Docker Engine / Docker Desktop (for containerized terminal sandboxes)

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest backend/tests/ -v        # Run all 45 automated tests
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run build                   # Verify production compilation (16/16 routes)
npm run dev -- -p 3000          # Launch dashboard at http://localhost:3000
```

### 4. Docker Compose Setup
```bash
docker compose up --build -d
```

---

## Documentation & Audits

All non-application documentation, architecture diagrams, audit reports, and engineering records are organized under [`docs/`](docs/README.md):

- **Architecture**: [`docs/architecture/UPDATED_ARCHITECTURE.md`](docs/architecture/UPDATED_ARCHITECTURE.md)
- **Remediation Report**: [`docs/reports/REMEDIATION_REPORT.md`](docs/reports/REMEDIATION_REPORT.md)
- **Security Audit**: [`docs/reports/SECURITY_REMEDIATION.md`](docs/reports/SECURITY_REMEDIATION.md)
- **Integration Test Results**: [`docs/reports/INTEGRATION_TEST_RESULTS.md`](docs/reports/INTEGRATION_TEST_RESULTS.md)
- **Issue Matrix & Release Assessment**: [`docs/reports/REMAINING_ISSUES.md`](docs/reports/REMAINING_ISSUES.md)
- **Contributing Guidelines**: [`docs/specifications/CONTRIBUTING.md`](docs/specifications/CONTRIBUTING.md)
