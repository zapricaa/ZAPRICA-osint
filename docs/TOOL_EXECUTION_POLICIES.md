# ZAPRICA — Tool Execution Policies Specification

## 1. Overview & Policy Architecture

In ZAPRICA, tools cannot be invoked arbitrarily by AI agents. Every tool invocation passes through a multi-layer verification gateway:

```
[Agent Tool Proposal]
        |
        v
[1. RBAC & User Permission Check]
        |
        v
[2. Investigation Scope Validation]
        |
        v
[3. Tool Approval & Active Status (TIMS)]
        |
        v
[4. Tool Execution Policy & Target Domain Policy]
        |
        v
[5. Argument Sanitization & Pydantic Validation]
        |
        v
[Isolated Execution (Playwright / Docker Sandbox)]
```

---

## 2. Policy Dimensions

Every registered tool in TIMS carries a `ToolExecutionPolicy`:

| Field | Type | Description |
| :--- | :--- | :--- |
| `tool_id` | String | Unique identifier of the tool. |
| `execution_mode` | Enum | `AUTOMATED`, `HUMAN_ASSISTED_ONLY`, `CONTAINER_SANDBOX`, `API_ONLY`, `DISABLED`. |
| `allowed_destinations` | JSON Array | Wildcard domain or IP patterns the tool is permitted to communicate with. |
| `blocked_destinations` | JSON Array | Explicitly denied destinations (e.g. internal CIDRs, cloud metadata). |
| `requires_human_approval`| Boolean | If true, tool invocation halts until an administrator or investigator approves. |
| `browser_automation_allowed`| Boolean | Whether headless or automated browser control is permitted. |
| `container_sandbox_required`| Boolean | Whether execution must run inside a container sandbox. |
| `max_execution_time_seconds`| Integer | Upper limit on runtime before termination (default 60s). |

---

## 3. Dedicated Tool Policies

### A. Epieos (`tool_id: epieos`)
- **Execution Mode**: `HUMAN_ASSISTED_ONLY`
- **Browser Automation Allowed**: `false`
- **Requires Human Approval**: `true`
- **Container Sandbox Required**: `false`
- **Permitted Flow**: The investigator operates Epieos manually via the visible browser interface; results are imported manually via `/browser/sessions/{session_id}/import-manual-result`. Automated scraping is strictly blocked by policy.

### B. Network & CLI Tools (`whois`, `dig`, `subfinder`, `exiftool`)
- **Execution Mode**: `CONTAINER_SANDBOX`
- **Browser Automation Allowed**: `false`
- **Container Sandbox Required**: `true`
- **Host Execution**: Prohibited (Fail-Closed).
- **Arguments**: Validated against Pydantic models; shell chaining and redirection characters are rejected.

### C. Web Extraction (`playwright_browser`)
- **Execution Mode**: `AUTOMATED` (Subject to target domain policy)
- **Browser Automation Allowed**: `true`
- **Egress Filter**: SSRF and RFC 1918 blocking enforced.

---

## 4. Policy Administration API

Administrators can inspect and configure execution policies via:
- `GET /api/v1/tools/{tool_id}/execution-policy` — View active policy.
- `PUT /api/v1/tools/{tool_id}/execution-policy` — Update policy parameters (Admin/Super Admin only).

> [!IMPORTANT]
> The security invariant for Epieos is immutable: Attempting to enable `browser_automation_allowed: true` on `tool_id: epieos` is rejected by the backend with HTTP 400.
