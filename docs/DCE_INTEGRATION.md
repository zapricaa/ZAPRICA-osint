# ZAPRICA — DCE (Data Collection Engine) Integration Specification

**Date**: 2026-11-02  
**Target Architecture**: Native Linux (Ubuntu LTS reference deployment)  
**Status**: Implemented & Verified  

---

## 1. Architectural Role & Execution Pipeline

The Data Collection Engine (DCE) provides a unified, highly controlled, and audited interface for data collection across command-line tools in isolated Docker sandboxes, authenticated external REST APIs, and synthetic demonstration fixtures.

```text
MAIN HEAD AGENT
       │
       ▼ (Task Planning & Target Scoping)
TIMS REGISTRY & RESOLVER
       │
       ▼ (Validated TaskEnvelope)
DCE COORDINATOR (backend/app/collection/coordinator.py)
       ├── CLI Adapters  ──► TerminalManager  ──► Docker Sandbox (Debian Bookworm, Non-Root)
       ├── API Adapters  ──► Direct HTTPX Client (HIBP API v3)
       └── Synthetic     ──► Deterministic In-Memory Fixtures
       │
       ▼ (RawCollectorOutput + Hashes)
EVIDENCE SERVICE (backend/app/services/evidence_service.py)
       ├── Raw Bytes Storage (Local FS / S3) + SHA-256 Digest
       ├── Unreviewed Finding Creation
       └── FindingSource Audit Linkage
       │
       ▼ (Structured FindingsPackage)
MAIN HEAD SYNTHESIZER
```

---

## 2. Integrated Data Collectors

### 2.1 WHOIS Domain Registration (`whois_lookup`)
- **Execution Mechanism**: CLI (`whois <target>` in Docker container).
- **Target Types**: `domain`.
- **Extracted Fields**: Registrar name, creation date, registry expiration date, last updated date, authoritative name servers, registrant organization, privacy redaction flags, domain status flags.
- **Fail-Closed Behavior**: If Docker is unavailable, fails closed with HTTP 503; zero host commands executed.

### 2.2 DNS Full Record Query (`dns_lookup`)
- **Execution Mechanism**: CLI (`dig +short +time=5 +tries=2 <target> <record_type>` in Docker container).
- **Target Types**: `domain`.
- **Supported Record Types**: `A`, `AAAA`, `MX`, `NS`, `TXT`, `CNAME`, `SOA`, `CAA`.
- **Extracted Fields**: Record types, values, MX priorities, TXT content, query timestamp, resolution warnings.

### 2.3 Have I Been Pwned (`hibp`)
- **Execution Mechanism**: Async HTTP API (`httpx.AsyncClient`).
- **Target Types**: `email`.
- **Authentication**: `HIBP_API_KEY` loaded securely from server settings.
- **Error Handling**:
  - `HTTP 404`: Clean account (zero breaches recorded).
  - `HTTP 429`: Rate limit handled with `retry-after` header backoff.
  - `HTTP 401/403`: Unauthorized or invalid key.

### 2.4 theHarvester (`theharvester`)
- **Execution Mechanism**: CLI (`theHarvester -d <domain> -b <sources> -l <limit>` in Docker container).
- **Target Types**: `domain`.
- **Supported Sources**: `crtsh` (Certificate Transparency) and public passive archives.
- **Extracted Fields**: Subdomains and verified public email addresses.

### 2.5 Sherlock (`sherlock`)
- **Execution Mechanism**: CLI (`sherlock --print-found --no-color --timeout 10 <username>` in Docker container).
- **Target Types**: `username`.
- **Output Constraints**: Candidate public profile URLs and matching service names.
- **Investigative Caution**: Matches are stored as low-confidence candidates with explicit disclaimer that username reuse is not proof of identity.

### 2.6 Holehe (`holehe`) — Restricted
- **Execution Mechanism**: CLI (`holehe --only-used --no-color <email>` in Docker container).
- **Target Types**: `email`.
- **Policy Invariant**: Disabled by default (`HOLEHE_ENABLED=false`). Requires explicit administrator enablement and human approval.

### 2.7 Synthetic Demo Collector (`demo_collector`)
- **Execution Mechanism**: In-process synthetic fixture.
- **Target Types**: `domain`, `email`, `username`.
- **Target Criteria**: Only responds to reserved identifiers (`*@demo.example`, `demo_*`, `demo.example`).
- **Safety Invariant**: Always sets `is_synthetic=True`. Never dispatches live network traffic.

---

## 3. Evidence & Provenance Pipeline

For every successful collector execution:
1. **Raw Preservation**: Original stdout/stderr bytes are stored via `EvidenceService.store_evidence`.
2. **Cryptographic Integrity**: SHA-256 digest is calculated immediately on ingestion.
3. **Traceability**: `EvidenceArtifact` records `source_url`, `collected_by`, execution duration, and exit code.
4. **Structured Findings**: `Finding` entities are created with `verification_status="unreviewed"`.
5. **FindingSource Linkage**: Many-to-many relationship links findings directly to the evidence artifact.

