# ZAPRICA System Architecture & End-to-End Workflow Map

This document explains in detail how all components, data structures, agents, databases, and security boundaries in ZAPRICA connect to each other.

---

## 1. Global System Flowchart

The following diagram maps the entire architecture from the user's browser down to low-level workers and back to the report dashboard:

```mermaid
flowchart TD
    %% User and UI Layer
    USER(["Investigator / Operator"]) --> |"Interacts with Cyber Dashboard"| UI["Next.js 14 Frontend UI (App Router)"]
    UI --> |"REST Requests with JWT & X-Workspace-ID"| API["FastAPI Backend (/v1)"]
    API --> |"Server-Sent Events (SSE)"| UI

    %% Security & Auth Gate
    subgraph S1 ["Security & Authorization Gate"]
        AUTH["Auth & RBAC Dependency (deps.py)"]
        SCOPE["Deterministic Scope Gate (InvestigationScope)"]
        AUDIT["Audit Service (Append-only AuditEvent)"]
    end

    API --> AUTH
    AUTH --> |"Authorized Workspace & Role"| SCOPE
    AUTH --> AUDIT

    %% Core Application Service Layer
    subgraph S2 ["Core Application Services"]
        INV_SRV["Investigation Service"]
        AUTH_SRV["Auth Service"]
        EVD_SRV["Evidence Service"]
        TOOL_SRV["TIMS Registry Service"]
        REP_SRV["Report Service"]
    end

    SCOPE --> INV_SRV
    API --> AUTH_SRV
    API --> TOOL_SRV
    API --> REP_SRV

    %% Persistence Layer
    subgraph S3 ["Persistence & Storage Layer"]
        DB[("PostgreSQL / SQLite Database\n(SQLAlchemy 2.0 Async Models)")]
        STORAGE[("Evidence Object Storage\n(Local Filesystem / S3-Compatible)")]
    end

    INV_SRV <--> DB
    AUTH_SRV <--> DB
    EVD_SRV <--> DB
    EVD_SRV <--> STORAGE
    TOOL_SRV <--> DB
    REP_SRV <--> DB
    AUDIT --> DB

    %% Multi-Agent System (3-Tier Hierarchy)
    subgraph S4 ["Multi-Agent Orchestration Subsystem"]
        MAIN["Main Head AI Agent (Supervisor - LangGraph)"]
        BH["Browser Head Sub-Head Agent"]
        TH["Terminal Head Sub-Head Agent"]
        
        %% Workers
        BW["Browser Workers (Playwright Runtime)"]
        TW["Terminal Workers (Sandboxed CLI Adapters)"]
        
        %% Deterministic Processors
        DPROC["Deterministic Processing Pipeline\n(Clean • Normalize • Deduplicate • Classify)"]
    end

    INV_SRV --> |"Trigger on /start"| MAIN
    MAIN --> |"Decompose into TaskEnvelopes"| BH
    MAIN --> |"Decompose into TaskEnvelopes"| TH

    BH --> |"Dispatch isolated browser task"| BW
    TH --> |"Dispatch schema-validated CLI task"| TW

    BW --> |"Raw HTML Snapshot & DOM Text"| EVD_SRV
    TW --> |"Raw Tool STDOUT/STDERR"| EVD_SRV

    BW --> |"Raw Output"| DPROC
    TW --> |"Raw Output"| DPROC

    DPROC --> |"Structured Derived Records"| EVD_SRV
    DPROC --> |"WorkerResultEnvelope"| BH
    DPROC --> |"WorkerResultEnvelope"| TH

    BH --> |"Browser FindingsPackage"| MAIN
    TH --> |"Terminal FindingsPackage"| MAIN

    MAIN --> |"Correlate, Detect Conflicts & Synthesize"| REP_SRV
    REP_SRV --> |"Final Traceable Report"| DB
```

---

## 2. The 3-Tier Agent Hierarchy & Communication Flow

ZAPRICA rejects flat, unrestricted chatbot architecture in favor of a strictly structured **3-Tier Agent Hierarchy**. Agent communication never uses loose natural language prompts as the sole contract; all communication is typed, versioned, and validated with Pydantic envelopes.

```mermaid
sequenceDiagram
    autonumber
    actor Inv as Investigator
    participant Main as Main Head Agent (Supervisor)
    participant Scope as Deterministic Scope Gate
    participant TIMS as Tool Registry (TIMS)
    participant BH as Browser Head Agent
    participant BW as Playwright Browser Worker
    participant Proc as Deterministic Processors
    participant Evd as Evidence Service
    participant Rep as Report Service

    Inv->>Main: Request Investigation (Target: example.com)
    Main->>Scope: Validate requested target & capability
    Scope-->>Main: Scope Validated (Allowed: example.com, Op: public_website_metadata)
    
    Main->>TIMS: Discover active tools for "public_website_metadata"
    TIMS-->>Main: Returns ToolVersion ID: "website_metadata.v1"
    
    Main->>Main: Decompose into TaskEnvelope
    Main->>BH: Route TaskEnvelope (Assigned: browser_head)
    
    BH->>BW: Execute isolated Playwright Context
    BW->>BW: SSRF Egress Filter: Resolve IP, block private/loopback/cloud metadata
    BW->>BW: Fetch webpage & extract title, headers, links, tech indicators
    
    BW->>Evd: Store immutable Raw HTML (calculate SHA-256)
    Evd-->>BW: Return EvidenceArtifact ID
    
    BW->>Proc: Send raw extracted snippets
    Proc->>Proc: Clean HTML (strip scripts/styles)
    Proc->>Proc: Normalize URLs, domains & emails
    Proc->>Proc: Deduplicate against existing findings
    Proc->>Proc: Classify finding type (e.g. tech_stack, contact)
    
    Proc->>Evd: Record Finding with Provenance Source link
    Proc-->>BH: Return WorkerResultEnvelope
    
    BH-->>Main: Return FindingsPackage (Findings, Evidence IDs, Status)
    Main->>Main: Check investigation completeness (Evaluate Gaps)
    Main->>Rep: Generate Structured Investigation Report
    Rep-->>Inv: Display in Workspace Dashboard (via SSE live update)
```

---

## 3. Tool Intelligence & Management System (TIMS) Lifecycle

New tools are added without changing core application or agent source code. A tool must pass through strict lifecycle states before being executable.

```mermaid
stateDiagram-v2
    [*] --> Draft: Admin registers tool metadata & manifest
    Draft --> Testing: Submit for isolated test validation
    Testing --> PendingReview: Automated tests pass in restricted container
    Testing --> Rejected: Validation failure or policy violation
    PendingReview --> Approved: Human Administrator signs approval
    PendingReview --> Rejected: Admin rejects tool
    Approved --> Published: Tool version published to Registry
    Published --> ActiveExecution: Agent capability discovery matches tool
    Published --> Disabled: Admin disables tool version
    Disabled --> Published: Admin re-enables tool version
    Published --> Revoked: Security issue identified
    Revoked --> [*]: Permanent block on execution
```

---

## 4. Evidence Provenance & Immutability Chain

Every insight shown to an investigator retains an unbroken chain of custody linked to raw artifacts:

```mermaid
flowchart LR
    subgraph Raw ["1. Immutable Raw Evidence"]
        RAW_BYTES["Raw HTML / Network Packets / Output Bytes"]
        HASH["SHA-256 Digest Calculation"]
        RAW_BYTES --> HASH
        HASH --> ARTIFACT["EvidenceArtifact Record\n(storage_uri, sha256, byte_size, collected_at)"]
    end

    subgraph Derivation ["2. Deterministic Derivation"]
        ARTIFACT --> PROCESSORS["Data Cleaners & Normalizers"]
        PROCESSORS --> DERIVED["Extracted Attributes\n(e.g., Server: nginx, Contact: info@target.com)"]
    end

    subgraph Provenance ["3. Finding & Provenance Linkage"]
        DERIVED --> FINDING["Finding Record\n(title, normalized_value, summary, confidence)"]
        FINDING --> SOURCE_LINK["FindingSource Record\n(finding_id, evidence_artifact_id, source_url, source_locator)"]
        ARTIFACT -.-> SOURCE_LINK
    end

    subgraph Synthesis ["4. Final Report"]
        FINDING --> REPORT["Report Section\n(Facts vs Inferences, Limitations, Source Citations)"]
    end
```

---

## 5. Security Egress & Sandboxing Architecture

To prevent Server-Side Request Forgery (SSRF) and host escape:

```mermaid
flowchart TD
    WORKER["Investigation Worker"] --> REQUEST{"Worker makes outbound request"}
    
    REQUEST --> DNS["DNS Resolution & Egress Policy Check"]
    
    DNS --> CHECK{"Is IP in forbidden range?"}
    CHECK -->|"127.0.0.0/8 (Loopback)"| BLOCK["DROP REQUEST & Log Security Audit Event"]
    CHECK -->|"10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (Private RFC1918)"| BLOCK
    CHECK -->|"169.254.169.254 (Cloud Metadata Service)"| BLOCK
    CHECK -->|"Reserved / Multicast / Link-local"| BLOCK
    
    CHECK -->|"Public Routable IP & Allowed Scope Target"| PERMIT["Allow outbound TLS/HTTPS connection"]
    PERMIT --> TARGET["Approved Public Target"]
```

---

## 6. Directory Structure Mapping

- `backend/app/core/`: Application settings, async database configuration, security (JWT/Bcrypt), event bus (SSE).
- `backend/app/models/`: SQLAlchemy 2.0 async database models (19 tables spanning users, workspaces, investigations, tasks, tools, evidence, entities, reports, audit).
- `backend/app/schemas/`: Pydantic 2.x request/response models conforming to `docs/API_SPEC.yaml`.
- `backend/app/services/`: Pure business logic (`AuthService`, `InvestigationService`, `EvidenceService`, `ToolService`, `ReportService`).
- `backend/app/storage/`: Pluggable evidence storage backends (`LocalStorageBackend`, `S3StorageBackend`).
- `backend/app/agents/`:
  - `contracts.py`: Typed envelopes for task dispatch, worker results, and findings packages.
  - `main_head/`: LangGraph orchestration supervisor.
  - `browser_head/`: Playwright supervisor and SSRF egress filter.
  - `terminal_head/`: Sandboxed CLI tool execution supervisor.
  - `workers/`: Web scrapers, CLI adapters, and deterministic data processors (`DataCleaner`, `DataNormalizer`, `DuplicateDetector`, `DataClassifier`).
- `frontend/src/app/`: Next.js 14 App Router pages (Dashboard, Investigations Workspace, Evidence Explorer, Agent Center, Tool Manager, Reports, Settings).
- `frontend/src/components/`: Reusable UI components (Sidebar, Navbar, Task Graph, Evidence Viewer).
- `docs/`: Technical specifications, architecture invariants, and database contracts.
- `WORK_LOG.md`: Master continuous execution tracker.
