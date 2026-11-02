# ZAPRICA — Remaining Issues & Future Roadmap

**Date**: 2026-11-02  
**Status**: UPGRADE REQUIREMENTS FULLY SATISFIED; PRODUCTION ENHANCEMENTS DOCUMENTED  

---

## 1. Status of Current Upgrade Requirements

All core architectural, security, database, agent hierarchy, and user interface requirements for the **Dedicated Browser & Terminal Agent Environment Upgrade** have been implemented and verified:

- [x] Dedicated Playwright browser environment replacing generic HTTP fetching.
- [x] User-isolated persistent browser profiles outside version control with path traversal defense.
- [x] Human login system with explicit `USER_AUTHENTICATED` confirmation protocol.
- [x] Website automation policies (`AUTOMATED_ALLOWED`, `HUMAN_ASSISTED_ONLY`, `API_ONLY`, `BLOCKED`).
- [x] Epieos special handling (`HUMAN_ASSISTED_ONLY`, manual user access, manual result import).
- [x] Dedicated Docker container execution environment with non-root user, read-only rootfs, tmpfs workspace, and dropped capabilities.
- [x] Strict fail-closed guarantee (zero host command execution fallback).
- [x] Terminal command allowlisting and injection defense.
- [x] Dedicated terminal workers and sorting & indexing processing worker.
- [x] Enriched `TaskEnvelope` contracts with scope, permitted domains/tools, execution mode.
- [x] Interactive `/browser` and `/terminal` frontend control centers.
- [x] 45/45 backend automated tests passing cleanly.
- [x] Next.js frontend compiling 16/16 routes without error.

---

## 2. Low-Priority Operational Considerations & Roadmap Enhancements

While all acceptance criteria are met, the following optional operational enhancements are recommended for long-term production scaling:

### 2.1 Remote VNC / WebRTC Browser Streaming
- **Current State**: The Browser Control Center provides visual confirmation via real-time proof screenshots (`POST /api/v1/browser/sessions/{session_id}/screenshot`) and interactive page navigation.
- **Enhancement**: Integrate an optional `noVNC` or WebRTC stream container (e.g. `kasmweb/chromium`) for real-time live video mirroring of the browser display when hosted remotely in headless cloud clusters.

### 2.2 Distributed Sandbox Worker Pool (Temporal / Celery)
- **Current State**: Docker sandboxes are provisioned and managed by the backend server's local Docker daemon.
- **Enhancement**: In large multi-tenant deployments with hundreds of concurrent investigations, offload sandbox dispatch to a distributed worker queue (such as Celery or Temporal) managing an elastic pool of remote sandbox runner nodes.

### 2.3 Additional OSINT CLI Adapter Registrations
- **Current State**: Initial approved adapters are implemented for `dns_lookup`, `whois_lookup`, `metadata_extractor`, `subdomain_enum`, and `cert_inspector`.
- **Enhancement**: As new tools are approved via TIMS (Tool Intelligence & Management System), register additional command specifications (e.g. `sherlock`, `theHarvester`, `amass`) within `TerminalExecutionPolicyValidator`.

