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

    %% 3-Tier Multi-Agent System
    subgraph S4 ["Multi-Agent Architecture (LangGraph Orchestration)"]
        MAIN["MAIN HEAD AI AGENT\n(Supervisor Graph Runner)"]
        BROWSER_HEAD["BROWSER HEAD AGENT\n(Web Reconnaissance)"]
        TERMINAL_HEAD["TERMINAL HEAD AGENT\n(Sandboxed CLI OSINT)"]
    end

    INV_SRV --> |"Trigger LangGraph Execution"| MAIN
    MAIN --> |"Task Envelope"| BROWSER_HEAD
    MAIN --> |"Task Envelope"| TERMINAL_HEAD

    %% Workers
    subgraph S5 ["Browser Workers & Data Processors"]
        PW["Playwright HTTP & DOM Worker"]
        SSRF["SSRF Egress Firewall"]
        CLEAN_B["Data Cleaning & Normalization"]
        DEDUP_B["Duplicate Detection"]
    end

    BROWSER_HEAD --> SSRF
    SSRF --> PW
    PW --> CLEAN_B
    CLEAN_B --> DEDUP_B
    DEDUP_B --> |"FindingsPackage"| BROWSER_HEAD

    subgraph S6 ["Terminal Workers & Data Processors"]
        GATEWAY["Controlled Tool Gateway\n(Strictly NO arbitrary shell)"]
        ADAPTERS["Approved Adapters\n(dns_lookup, whois_lookup, etc.)"]
        CLEAN_T["Normalization & Classification"]
        DEDUP_T["Duplicate Detection"]
    end

    TERMINAL_HEAD --> GATEWAY
    GATEWAY --> ADAPTERS
    ADAPTERS --> CLEAN_T
    CLEAN_T --> DEDUP_T
    DEDUP_T --> |"FindingsPackage"| TERMINAL_HEAD

    %% Evidence Pipeline
    BROWSER_HEAD --> |"Raw Evidence Artifact + SHA-256"| EVD_SRV
    TERMINAL_HEAD --> |"Raw Evidence Artifact + SHA-256"| EVD_SRV
    BROWSER_HEAD --> |"Consolidated Findings"| MAIN
    TERMINAL_HEAD --> |"Consolidated Findings"| MAIN

    MAIN --> |"Synthesize Report (Facts vs Inferences)"| REP_SRV
    REP_SRV --> |"Final Intelligence Report"| DB
```

---

## 2. 3-Tier Agent Hierarchy & Decision Cycle

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Investigator / Analyst
    participant API as FastAPI Backend
    participant MainHead as Main Head Agent (LangGraph)
    participant ScopeGate as Scope & Permission Gate
    participant BrowserHead as Browser Head Agent
    participant TerminalHead as Terminal Head Agent
    participant EvdService as Evidence & Provenance Service
    participant Storage as Raw Object Storage

    Analyst->>API: POST /v1/investigations (Target, Objective, Scope)
    API->>MainHead: Initialize InvestigationState
    MainHead->>ScopeGate: Validate Target against Allowed Scope & Policy
    alt Target Denied / Out-of-Scope
        ScopeGate-->>MainHead: Scope Violation (Halt with Error)
        MainHead-->>API: Investigation Marked Failed (Event Published)
    else Target Approved
        ScopeGate-->>MainHead: Scope Verified (Allow Execution)
        MainHead->>MainHead: Decompose Plan into Sub-Tasks (Pydantic Schemas)
        
        par Web Reconnaissance
            MainHead->>BrowserHead: Dispatch TaskEnvelope (public_website_metadata)
            BrowserHead->>BrowserHead: SSRF Filter (Block Private IPs/Loopback/Metadata)
            BrowserHead->>BrowserHead: Fetch Web Page & Extract Metadata
            BrowserHead->>EvdService: Store Raw HTML Payload
            EvdService->>Storage: Persist Blob & Calculate SHA-256 Hash
            Storage-->>EvdService: Storage URI & Digest
            BrowserHead->>BrowserHead: Clean, Normalize, Deduplicate Data
            BrowserHead-->>MainHead: Return FindingsPackage (Links to Evidence ID)
        and Network Reconnaissance
            MainHead->>TerminalHead: Dispatch TaskEnvelope (dns_lookup / whois_lookup)
            TerminalHead->>TerminalHead: Reject Raw Shell Strings (Enforce Tool Adapters)
            TerminalHead->>TerminalHead: Execute Tool Adapter in Isolation Container
            TerminalHead->>EvdService: Store Raw DNS/WHOIS Output
            EvdService->>Storage: Persist Blob & Calculate SHA-256 Hash
            Storage-->>EvdService: Storage URI & Digest
            TerminalHead->>TerminalHead: Clean, Normalize, Deduplicate Data
            TerminalHead-->>MainHead: Return FindingsPackage (Links to Evidence ID)
        end
        
        MainHead->>MainHead: Consolidate Cross-Source Findings & Deduplicate
        MainHead->>MainHead: Detect Conflicts & Information Gaps
        MainHead->>MainHead: Synthesize Report (Separate Facts vs Inferences)
        MainHead->>API: Mark Completed & Publish SSE Events
        API-->>Analyst: Live Dashboard Updates & Complete Report
    end
```

---

## 3. Tool Intelligence & Management System (TIMS) Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft: Administrator Submits Tool Manifest & Doc
    Draft --> PlaybookGenerated: System Extracts Structured Playbook (JSON Schema)
    PlaybookGenerated --> Validating: Run Automated Sandbox Test in Isolation
    
    state Validating {
        [*] --> CheckSchema: Validate Parameter Constraints
        CheckSchema --> CheckExecution: Execute in Non-Root Ephemeral Sandbox
        CheckExecution --> CheckOutput: Verify Output Matches Expected Schema
    }
    
    Validating --> Rejected: Validation Failed / Policy Violation
    Validating --> PendingApproval: Validation Passed (Exit Code 0, Valid Schema)
    
    PendingApproval --> Approved: Super Admin Reviews and Approves
    PendingApproval --> Rejected: Admin Denies Approval
    
    Approved --> Published: Assigned to Permitted Agents
    Published --> Disabled: Admin Emergency Kill-Switch (Immediate Revocation)
    Disabled --> Published: Admin Re-enables Tool
    Published --> [*]
```

---

## 4. Evidence Integrity & Provenance Chain

```mermaid
flowchart LR
    RAW["Raw Collector Output (HTML, DNS, WHOIS)"] --> HASH["Compute SHA-256 Cryptographic Hash"]
    HASH --> STORE["Immutable Object Storage (Local / S3)"]
    STORE --> ARTIFACT["EvidenceArtifact Record\n(Storage URI, Hash, Timestamp, Collector)"]
    
    ARTIFACT --> SOURCE["FindingSource Join Table\n(Artifact ID, URL, Locator, Relationship)"]
    SOURCE --> FINDING["Derived Finding Record\n(Type, Normalized Value, Confidence)"]
    
    FINDING --> ENTITY["Knowledge Graph Entity\n(Domain, IP, Org, Email, Person)"]
    FINDING --> REPORT["Intelligence Report\n(Observed Facts vs Inferred Hypotheses)"]
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

## 6. Google Gemini AI Brain & Safe Startup Mode

```mermaid
flowchart TD
    subgraph STARTUP ["Application Startup Phase"]
        BOOT["FastAPI Lifespan Startup"] --> DB_CHECK["1. Read-Only DB Health Check (SELECT 1)"]
        DB_CHECK --> AI_INIT["2. Passive AI Provider Config (google-genai Client)"]
        AI_INIT --> AGENT_IDLE["3. Set Main Head, Browser Head, Terminal Head to IDLE"]
        AGENT_IDLE --> WORKER_OFF["4. Set Workers to DISABLED"]
        WORKER_OFF --> SAFE_FLAGS["5. Enforce Safe Mode Flags\n(SAFE_MODE=true, TERMINAL_EXEC=false, AUTO_INV=false)"]
    end

    subgraph RUNTIME ["Authenticated User Runtime"]
        USER_REQ["Authenticated User Explicit Request"] --> SCOPE_VERIFY["Check Scope & Permitted Operations"]
        SCOPE_VERIFY --> AI_REASONING["AI Brain Structured Reasoning (gemini-3.8-flash)"]
        
        AI_REASONING --> PROPOSAL{"Agent proposes Tool Call"}
        PROPOSAL --> PERM_CHECK{"Is Terminal Exec Enabled & User Permitted?"}
        
        PERM_CHECK -->|"Disabled by Safe Mode"| BLOCK_TOOL["HTTP 403: Blocked by Safe Mode\n(Admin Activation Required)"]
        PERM_CHECK -->|"Enabled & Authorized"| GATEWAY_EXEC["Controlled Tool Gateway Adapter\n(Strictly NO arbitrary shell)"]
    end

    SAFE_FLAGS --> RUNTIME
```

---

## 7. Invite-Only Authentication & Session Verification

```mermaid
flowchart TD
    subgraph ONBOARDING ["Invite-Only User Provisioning"]
        SUPER["Super Admin"] -->|"1. Generates Secure Invitation"| INV["Invitation Token (7-Day Expiry, SHA-256 Hashed)"]
        INV -->|"2. Invitee Receives Link"| ACCEPT["/v1/auth/accept-invitation"]
        ACCEPT -->|"3. Sets Password (Argon2id) & Username"| ACTIVE_USER["Active User Account + Role Assigned"]
    end

    subgraph AUTHENTICATION ["Multi-Factor Login Pipeline"]
        LOGIN["POST /v1/auth/login (Username/Email + Password)"] --> LOCKOUT{"Failed Attempts >= 5 in 15min?"}
        LOCKOUT -->|"Yes"| LOCKED["HTTP 423: Account Temporarily Locked"]
        LOCKOUT -->|"No"| VERIFY_PWD{"Argon2id Hash Matches?"}
        
        VERIFY_PWD -->|"Mismatch"| LOG_FAIL["Log to login_attempts & Increment Counter"]
        VERIFY_PWD -->|"Match"| STATUS_CHECK{"Account Status == 'active'?"}
        
        STATUS_CHECK -->|"Suspended / Disabled / Revoked"| FORBIDDEN["HTTP 403: Account Inactive"]
        STATUS_CHECK -->|"Active"| MFA_CHECK{"MFA Enabled?"}
        
        MFA_CHECK -->|"Yes & No Code"| MFA_PROMPT["HTTP 402: MFA Code Required"]
        MFA_CHECK -->|"Yes & Valid TOTP"| ISSUE_SESSION["Create Session & Set HttpOnly Cookie"]
        MFA_CHECK -->|"No"| ISSUE_SESSION
        
        ISSUE_SESSION --> JWT["Return Signed JWT + Session Token"]
    end
```


---

## 8. Frontend UI & Component Route Map

```mermaid
flowchart TD
    ROOT["Root Entry (/)"] --> REDIRECT{"Authenticated?"}
    REDIRECT -->|"No"| LOGIN["/login (Argon2id + TOTP Challenge)"]
    REDIRECT -->|"Yes"| DASHBOARD["/dashboard (Metrics, Safe Mode, Fleet Status)"]
    
    LOGIN --> ACCEPT["/accept-invitation (Token Activation)"]
    
    subgraph APP_SHELL ["ZAPRICA Application Shell (Sidebar + Navbar)"]
        DASHBOARD
        
        subgraph INVESTIGATIONS ["Investigation Domain"]
            INV_LIST["/investigations (Workspaces Catalogue)"]
            INV_NEW["/investigations/new (Target Wizard + Scope Allow/Deny)"]
            INV_DETAIL["/investigations/[id] (Live Workspace, LangGraph Stages, SSE Stream)"]
        end
        
        subgraph INTELLIGENCE ["Intelligence & Evidence"]
            EVD["/evidence (SHA-256 Provenance Explorer)"]
            REP["/reports (Empirical Facts vs Inferences Separation)"]
        end
        
        subgraph MANAGEMENT ["System & Administration"]
            TOOLS["/tools (TIMS Sandbox Testing & Approval Lifecycle)"]
            AGENTS["/agents (Main Head, Browser Head, Terminal Head Supervision)"]
            ADMIN["/admin (User Management, Invites, Sessions, Terminal Exec Toggle)"]
        end
    end
    
    INV_NEW --> INV_DETAIL
    INV_DETAIL --> REP
    INV_DETAIL --> EVD
```

---

## 9. Deployment Architecture & Docker Multi-Service Topology

```mermaid
flowchart LR
    subgraph CLIENT ["Client Tier"]
        BROWSER["Web Browser / Security Analyst"]
    end

    subgraph DOCKER_NETWORK ["Isolated Docker Bridge Network (zaprica-net)"]
        FRONTEND["frontend:3000\n(Next.js 14 Production Server)"]
        BACKEND["backend:8000\n(FastAPI / Uvicorn Application Server)"]
        POSTGRES[("db:5432\n(PostgreSQL 16 Alpine Database)")]
        SANDBOX["Isolated Container Sandbox\n(Ephemeral Tool Execution)"]
    end

    BROWSER -->|"HTTPS / Port 3000"| FRONTEND
    FRONTEND -->|"Internal Proxy (/api & SSE)"| BACKEND
    BACKEND <-->|"Async SQLAlchemy / asyncpg"| POSTGRES
    BACKEND -->|"Controlled Tool Gateway API"| SANDBOX
    BACKEND -->|"Egress Proxy & Firewall"| INTERNET["Target OSINT Targets (Internet)"]
```
