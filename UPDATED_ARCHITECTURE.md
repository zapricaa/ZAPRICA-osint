# ZAPRICA — Updated System Architecture Specification

**Date**: 2026-11-02  
**Version**: 0.2  
**Status**: APPROVED & IMPLEMENTED  

---

## 1. System Overview & The 3-Tier Hierarchy

ZAPRICA implements an intelligence platform governed by a 3-tier multi-agent hierarchy:

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
         |  BROWSER SECURITY VALIDATOR |                   |       TERMINAL MANAGER      |
         |  (SSRF, RFC1918, Cloud IP)  |                   |   (Execution Coordinator)   |
         +--------------+--------------+                   +--------------+--------------+
                        |                                                 |
         +--------------v--------------+                   +--------------v--------------+
         |       BROWSER MANAGER       |                   |    DOCKER SANDBOX MANAGER   |
         | (Playwright Chromium Engine)|                   | (Isolated Non-Root Sandbox) |
         +--------------+--------------+                   +--------------+--------------+
                        |                                                 |
      +-----------------+-----------------+             +-----------------+-----------------+
      |                 |                 |             |                 |                 |
      v                 v                 v             v                 v                 v
[Playwright Worker] [DOM Extraction] [Screenshot]  [CLI OSINT]    [Network Intel]    [Metadata/Doc]
      |                 |                 |             |                 |                 |
      +-----------------+-----------------+             +-----------------+-----------------+
                        |                                                 |
                        v                                                 v
        [Data Cleaning & Deduplication]                 [Data Cleaning & Deduplication]
                        |                                                 |
                        v                                                 v
        [Sorting & Indexing Worker]                     [Sorting & Indexing Worker]
                        |                                                 |
                        +-----------------------+-------------------------+
                                                |
                                                v (FindingsPackage + SHA-256 Hashes)
                                +-------------------------------+
                                |       MAIN HEAD SYNTHESIZER   |
                                +---------------+---------------+
                                                |
                                                v
                                +-------------------------------+
                                |   INTELLIGENCE REPORT SERVICE |
                                | (Facts vs Inferences Provenance)
                                +-------------------------------+
```

---

## 2. Dedicated Browser Subsystem Architecture

### 2.1 Component Structure
- `backend/app/browser/browser_manager.py`: Controls the Playwright Chromium lifecycle, persistent browser contexts, page creation, interactive navigation, screenshot capture, and HTML/text extraction.
- `backend/app/browser/browser_policy.py`: Enforces target domain automation policies (`AUTOMATED_ALLOWED`, `HUMAN_ASSISTED_ONLY`, `API_ONLY`, `BLOCKED`). Protects Epieos as manual-only.
- `backend/app/browser/browser_security.py`: Intercepts SSRF attempts by resolving hostnames and validating target IP addresses against RFC 1918, loopbacks, and cloud metadata. Re-evaluates redirects in real time.
- `backend/app/browser/profile_manager.py`: Partitions persistent browser profiles by user ID outside version control (`data/browser_profiles/<user_id>/<profile_name>/`). Rejects path traversal attacks.
- `backend/app/browser/session_manager.py`: Manages the browser session state machine, tracking timestamps, current URLs, and the human confirmation protocol (`LOGIN_REQUIRED` -> `USER_AUTHENTICATED`).

### 2.2 Human Login Flow Protocol
1. On encountering login screens or MFA, the session transitions to `LOGIN_REQUIRED`.
2. The investigator opens the visible browser workspace at `/browser`.
3. The investigator signs in manually, completes MFA/CAPTCHA, and clicks **"CONFIRM USER AUTHENTICATED"**.
4. The system logs an immutable `BrowserSessionEvent` with the investigator's ID and transitions the session to `USER_AUTHENTICATED`.
5. Only then does the Browser Head resume automated tasks.

---

## 3. Dedicated Terminal Subsystem Architecture

### 3.1 Component Structure
- `backend/app/terminal/terminal_manager.py`: Coordinates terminal environments, task execution requests, and audit log generation.
- `backend/app/terminal/sandbox_manager.py`: Manages Docker container sandboxes with hardened flags:
  - `--read-only` rootfs
  - `--tmpfs /workspace:rw,noexec,nosuid,size=64m`
  - `--user 10001:10001` (non-root)
  - `--cap-drop=ALL`
  - `--security-opt=no-new-privileges`
  - `--pids-limit=64`
  - `-m 256m` / `--cpus 0.5`
- `backend/app/terminal/execution_policy.py`: Enforces approved command specifications (`dns_lookup`, `whois_lookup`, `metadata_extractor`, `subdomain_enum`, `cert_inspector`). Strictly blocks shell metacharacters and subshells.
- `backend/app/agents/workers/terminal_workers.py`: Specialized workers for CLI OSINT, Network Intel, Metadata Analysis, and Document Processing.

### 3.2 Fail-Closed Guarantee
Under NO circumstances does ZAPRICA fall back to executing commands on the host operating system. If Docker is offline or disabled, terminal tasks are rejected with HTTP 503 Service Unavailable.

---

## 4. Processing Workers Pipeline

Both Browser Head and Terminal Head feed raw evidence through deterministic processing workers before assembling findings packages:

1. **Data Cleaning Worker**: Normalizes line endings, strips ANSI escape sequences, removes null bytes, and trims whitespace.
2. **Duplicate Detection Worker**: Computes deterministic content hashes, flagging duplicate findings across sources.
3. **Sorting & Indexing Worker**: Sorts findings deterministically by timestamp, confidence score, and entity key, indexing them for rapid synthesis by the Main Head.

---

## 5. Frontend Workspaces & Integration

- **Browser Control Center (`/browser`)**: Real-time browser session control, URL navigation, proof screenshot preview, human login banner, and manual Epieos import modal.
- **Terminal Control Center (`/terminal`)**: Interactive terminal console with sandbox status indicators, tool launcher form, and real-time ANSI log stream.
- **Agent Control Center (`/agents`)**: Unified supervision dashboard displaying the operational states of the Main Head, Browser Head, and Terminal Head.
