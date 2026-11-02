# ZAPRICA — DCE (Data Collection Engine) Security & Isolation Controls

**Date**: 2026-11-02  
**Role**: Linux Security Engineer & DevSecOps Lead  
**Classification**: Technical Security Documentation  

---

## 1. Security Invariants & Threat Model

The DCE handles execution of external binaries and queries to third-party endpoints. It enforces five strict defense-in-depth layers:

```text
Layer 1: Input Validation & Shell Injection Prevention
Layer 2: Scope Enforcement & Investigation Authorization
Layer 3: Docker Sandbox Boundary (Non-Root, Cap-Drop, Read-Only)
Layer 4: Outbound Network & SSRF Egress Restrictions
Layer 5: Evidence Integrity & SHA-256 Provenance
```

---

## 2. Layer 1: Shell Injection & Argument Sanitization

- **No Shell Execution**: All CLI invocations use `subprocess.run(argv, shell=False)`.
- **Fixed Executable Mappings**: Binary names are hardcoded in `APPROVED_COMMANDS`.
- **Argument Builders**: User dictionary values are never appended directly to argv. Each adapter invokes `TerminalExecutionPolicyValidator.build_argv(tool_id, arguments)` which explicitly validates types and regex.
- **Flag Injection Guard**: Target identifiers (`domain`, `username`, `email`) must never start with a hyphen (`-`).
- **Disallowed Metacharacters**: `DANGEROUS_PATTERNS` strictly rejects `;`, `&`, `|`, `` ` ``, `$`, `>`, `<`, and command substitution.

---

## 3. Layer 2: Scope Enforcement & RBAC Authorization

- **Investigation Boundary**: Every collector job requires a valid `investigation_id`.
- **Denylist Check**: Target is compared against `scope.denied_targets`.
- **Allowlist Check**: Target must be within `scope.allowed_targets`.
- **Role Verification**:
  - `INVESTIGATOR`, `ADMINISTRATOR`, and `SUPER_ADMIN` can submit collection jobs.
  - `ANALYST` role is restricted to read-only access (cannot initiate collections).
- **Holehe Gating**: Holehe is disabled by default (`settings.HOLEHE_ENABLED=false`). When enabled, requires administrator approval.

---

## 4. Layer 3: Docker Sandbox Boundary

All CLI tool executions are dispatched inside ephemeral Docker containers managed by `DockerSandboxManager`:

| Hardening Flag | Setting | Security Purpose |
| :--- | :--- | :--- |
| **User** | `--user=10001:10001` | Non-root execution (`zapricasandbox`). |
| **Root Filesystem** | `--read-only` | Prevents filesystem tampering or rootkit installation. |
| **Volatile Storage** | `--tmpfs=/tmp:rw,noexec,nosuid,size=64m` | In-memory temporary scratch space only. |
| **Linux Capabilities** | `--cap-drop=ALL` | Drops all capabilities (no raw sockets, no ptrace, no chown). |
| **Privileges** | `--security-opt=no-new-privileges:true` | Prevents setuid binaries from escalating permissions. |
| **Resource Limits** | `--cpus=1.0 --memory=512m` | Prevents CPU starvation or memory exhaustion. |
| **Process Limits** | `--pids-limit=64` | Anti-forkbomb defense. |
| **Container Lifecycle** | `--rm` | Ephemeral container is destroyed immediately upon completion. |

---

## 5. Layer 4: SSRF Egress & Network Restrictions

- Target domains and URLs are pre-filtered via `SSRFEgressFilter.resolve_and_validate()` before socket or container operations.
- RFC 1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and cloud metadata (`metadata.google.internal`) are rejected with HTTP 403.
- `docker/sandbox` containers communicate across an isolated bridge network with zero access to the host loopback or database container.

---

## 6. Layer 5: Fail-Closed Security Guarantee

If the Docker daemon is offline or unverified, ZAPRICA strictly **fails closed**:
- Raises `HTTP 503 Service Unavailable`.
- Never executes commands directly on the host operating system.
- Never fabricates synthetic success output to disguise offline infrastructure.

