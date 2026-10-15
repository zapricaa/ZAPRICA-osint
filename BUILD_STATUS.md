# ZAPRICA Build Status & Implementation Log

## Platform Overview
**ZAPRICA** is an AI-powered autonomous OSINT investigation platform. The presentation layer provides a live, interactive link-analysis graph, case management workspace, and cryptographic evidence provenance ledger.

---

## Frontend Implementation Status (Verified)

### 1. Technology Stack & Framework
- **Framework**: Next.js 16.4.1 (React 19, TypeScript 5, App Router with Turbopack)
- **Graph Visualization**: `react-force-graph-2d` with dynamic client-side rendering (SSR disabled), custom node canvas painting, directional particles, node halos, and WebGL acceleration
- **State Management**: `zustand` (v5.0.15) for responsive client-side state handling
- **Icons**: `lucide-react` (v1.57.0)
- **Styling**: Vanilla CSS Design System with CSS Custom Properties, glassmorphism (`backdrop-filter`), cyber dark palette (`#060911` base with Cyan, Emerald, Amber, Violet, Rose accents), and micro-animations
- **Testing**: `vitest` (v5.0.4) + `@testing-library/react` (v16.3.3) + `@testing-library/jest-dom` (v7.0.1) + `jsdom` (v29.1.1)

---

### 2. Architecture & File Catalog

| File Path | Status | Purpose & Description |
| :--- | :--- | :--- |
| `frontend/src/types/index.ts` | Created | Complete TypeScript interfaces matching backend models (`Investigation`, `Entity`, `Evidence`, `ActivityLog`, `GraphResponse`, `Tool`, `HealthResponse`) |
| `frontend/src/lib/api.ts` | Created | Dual-mode API client communicating with FastAPI backend `/api` endpoints, with automatic health checking and isolated fallback handling |
| `frontend/src/lib/fixtures.ts` | Created | Strictly labeled offline development fixtures (`is_fixture: true`) with realistic threat intelligence cases, entities, and cryptographic SHA-256 evidence |
| `frontend/src/lib/store.ts` | Created | Global Zustand store for investigations, active case selection, tab switching, search/filter state, modals, and tool execution |
| `frontend/src/app/globals.css` | Modified | Cyber OSINT design system tokens, glassmorphic panels, badges, buttons, tables, custom scrollbars, and pulsing radar indicators |
| `frontend/src/app/layout.tsx` | Modified | Platform metadata, title, and clean HTML structure |
| `frontend/src/app/page.tsx` | Modified | Home view coordinating Header, StatsCards, InvestigationList, InvestigationWorkspace, and Modals |
| `frontend/src/components/Header.tsx` | Created | Platform header with logo, live backend connection indicator (`LIVE API (8000)` vs `FIXTURE MODE`), global search, and action triggers |
| `frontend/src/components/StatsCards.tsx` | Created | Metric cards (Total Investigations, Correlated Entities, Cryptographic Evidence, Autonomous Tools) and dev fixture warning banner |
| `frontend/src/components/InvestigationList.tsx` | Created | Investigation list with status filtering (All, Active, Paused, Completed), search query matching, refresh button, and empty states |
| `frontend/src/components/InvestigationCard.tsx` | Created | Case card with status pill, seed entity indicator, entity/evidence counters, status toggle, delete, and workspace button |
| `frontend/src/components/CaseCreationModal.tsx` | Created | Case creation dialog with input validation, entity type selection, and DPDP Act Section 3(c)(ii) legal attestation checkbox |
| `frontend/src/components/InvestigationWorkspace.tsx` | Created | Case workspace with multi-tab navigation: Graph, Entities, Evidence Ledger, Timeline, and OSINT Tool Console |
| `frontend/src/components/graph/IntelligenceGraph.tsx` | Created | Interactive graph container with entity filter pills, node count stats, node inspector drawer, and edge inspector drawer |
| `frontend/src/components/graph/ForceGraphInner.tsx` | Created | Custom 2D canvas force graph renderer with entity-specific colors, labels, selection halo, and directional particles |
| `frontend/src/components/workspace/EntitiesTable.tsx` | Created | Filterable and searchable table of resolved entities with indicator copy, confidence badges, provenance tags, and pivot actions |
| `frontend/src/components/workspace/EvidenceLedger.tsx` | Created | Cryptographic evidence ledger with SHA-256 digest copying, ISO-8601 timestamps, raw artifact inspection modal, and manual ingestion |
| `frontend/src/components/workspace/ActivityTimeline.tsx` | Created | Chronological audit trail showing agent actions, actor attribution (`user`, `system`), and JSON detail payloads |
| `frontend/src/components/workspace/ToolConsole.tsx` | Created | Tool console to dispatch DNS, HTTP, TLS, RDAP, or Webpage metadata queries directly against active investigation targets |
| `frontend/src/components/ToolRunnerModal.tsx` | Created | Global tool execution modal accessible from the header to run standalone or case-linked queries |
| `frontend/src/test/api.test.ts` | Created | Unit tests verifying live vs fixture API fallback and tool execution |
| `frontend/src/test/store.test.ts` | Created | Unit tests verifying Zustand state store actions and data loading |
| `frontend/src/test/components.test.tsx` | Created | Component tests verifying Header, StatsCards, InvestigationCard, and CaseCreationModal |
| `frontend/src/test/setup.ts` | Modified | Test configuration with `@testing-library/jest-dom/vitest` |
| `frontend/vitest.config.mts` | Created | Vitest runner configuration with `@vitejs/plugin-react` and path aliases |
| `frontend/tsconfig.json` | Modified | Excludes test files from Next.js production build bundle |
| `frontend/next.config.ts` | Modified | Configures API rewrites to proxy `/api/*` to `http://localhost:8000/api/*` |
| `frontend/package.json` | Modified | Added testing scripts (`test`, `test:watch`) and devDependencies |

---

### 3. Test Verification (`npm test`)

Executed from `frontend/` directory:
```text
> frontend@0.1.0 test
> vitest run

 RUN  v5.0.4 E:/test/ZAPRICA-osint/frontend

 ✓ src/test/smoke.test.ts (1 test)
 ✓ src/test/api.test.ts (4 tests)
 ✓ src/test/store.test.ts (5 tests)
 ✓ src/test/components.test.tsx (4 tests)

 Test Files  4 passed (4)
      Tests  14 passed (14)
   Duration  4.03s
```
**Status: 100% Passed (14 of 14 tests passing).**

---

### 4. Production Build Verification (`npm run build`)

Executed from `frontend/` directory:
```text
> frontend@0.1.0 build
> next build

▲ Next.js 16.4.1 (Turbopack)
✓ Running next.config.ts took 1403ms
  Creating an optimized production build ...
✓ Compiled successfully in 7.4s
  Running TypeScript ...
  Finished TypeScript in 4.6s ...
  Collecting page data using 5 workers ...
  Generating static pages using 5 workers (0/4) ...
✓ Generating static pages using 5 workers (4/4) in 1574ms
  Finalizing page optimization ...

Route (app)
┌ ○ /
└ ○ /_not-found

○  (Static)  prerendered as static content
```
**Status: Exit Code 0 (Production build succeeded with zero errors).**

---

### 5. Backend API Verification Matrix

The frontend API integration was verified against the FastAPI backend endpoints:

| Endpoint | Method | Tested Status | Actual Backend Response / Observation |
| :--- | :--- | :--- | :--- |
| `/api/health` | `GET` | **PASS (200)** | Returns `{"status": "healthy", "version": "0.1.0", "database": "sqlite (development)"}` |
| `/api/tools` | `GET` | **PASS (200)** | Returns 5 registered OSINT tools (`dns_lookup`, `http_metadata`, `tls_certificate`, `rdap_lookup`, `webpage_metadata`) |
| `/api/tools/execute` | `POST` | **PASS (200)** | Standalone tool execution (e.g., `dns_lookup` for domain) executes live and returns parsed DNS records with SHA-256 hash |
| `/api/investigations` | `GET` | **PASS (200)** | Returns `{"investigations": [], "total": 0}` from local SQLite database |
| `/api/investigations` | `POST` | **DEFECT (500)** | Backend raises `(sqlite3.IntegrityError) NOT NULL constraint failed: activity_logs.investigation_id` because `inv.id` is not flushed before logging creation |

**Integration Isolation**:
Because backend `POST /api/investigations` currently fails due to the un-flushed `inv.id` defect in `investigations.py`, the frontend's built-in fallback system cleanly catches this and isolates clearly labeled development fixtures (`DEV FIXTURE (LIVE BACKEND OFFLINE)`). The analyst is informed of fixture status and mock data is never claimed to be real.

---

### 6. Action Items for Backend / Architect Agent
1. **Fix `create_investigation` in `backend/app/routes/investigations.py`**:
   Add `await db.flush()` after `db.add(inv)` (around line 60) before instantiating `Entity(investigation_id=inv.id, ...)` and `ActivityLog(investigation_id=inv.id, ...)`. This will resolve the SQLite NOT NULL constraint error and enable live case creation.
2. **Database Auto-Initialization**:
   Ensure `await init_db()` runs reliably when launching the application via `uvicorn app.main:app` so tables exist on fresh deployments.
