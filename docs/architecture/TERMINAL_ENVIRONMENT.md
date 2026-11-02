# ZAPRICA — Dedicated Terminal Environment Documentation

## 1. Architectural Overview

The Terminal Head Agent governs a strictly controlled, isolated execution gateway. Agent-generated terminal commands are NEVER executed directly on the host operating system.

```
+-------------------------------------------------------------------+
|                     TERMINAL HEAD AGENT                           |
|             (Supervised Gemini 3.5 Flash Lite)                    |
+---------------------------------+---------------------------------+
                                  |
               +------------------v------------------+
               |      TERMINAL EXECUTION POLICY      |
               |  (Allowlisted Commands & Pydantic)  |
               +------------------+------------------+
                                  |
               +------------------v------------------+
               |           TERMINAL MANAGER          |
               |   (Coordinates Sandbox Execution)   |
               +------------------+------------------+
                                  |
               +------------------v------------------+
               |        DOCKER SANDBOX MANAGER       |
               |      (Isolated Alpine Sandbox)      |
               +-------------------------------------+
```

---

## 2. Hardened Sandbox Specifications

Every terminal container executes under hardened security controls:

| Security Dimension | Sandbox Configuration |
| :--- | :--- |
| **Root Filesystem** | `--read-only` (Immutable root; agents cannot write to `/bin`, `/usr`, or system binaries) |
| **Workspace** | `--tmpfs /workspace:rw,noexec,nosuid,size=64m` (Volatile in-memory scratch space) |
| **User Identity** | `--user 10001:10001` (Non-root unprivileged execution) |
| **Privilege Escalation** | `--security-opt=no-new-privileges` (Blocks setuid/setgid privilege acquisition) |
| **Linux Capabilities** | `--cap-drop=ALL` (Drops all kernel capabilities including CAP_NET_ADMIN, CAP_SYS_ADMIN) |
| **PID Limits** | `--pids-limit=64` (Preempts fork bombs and runaway subprocesses) |
| **Memory Limit** | `-m 256m` (Restricts memory abuse) |
| **CPU Limit** | `--cpus 0.5` (Prevents CPU starvation) |
| **Host Mounts** | Prohibited. Host `/`, `/root`, `/home`, Windows drives `C:\`, `E:\`, and `/var/run/docker.sock` are NEVER mounted. |

---

## 3. Strict Fail-Closed Guarantee

If Docker is not running, daemon is unreachable, or the sandbox container fails to initialize:
- **Rule**: The application MUST fail closed.
- **Enforcement**: Under no circumstances will ZAPRICA fall back to running commands on the host machine (`powershell.exe`, `cmd.exe`, or host bash).
- **HTTP Response**: The request is rejected immediately with `HTTP 503 Service Unavailable`:
  `"Docker sandbox is offline and terminal execution is strictly isolated. Host execution is prohibited (Fail-Closed)."`

---

## 4. Command Allowlist & Argument Validation

Terminal workers cannot execute arbitrary shell syntax. Every command is defined as a validated specification in `TerminalExecutionPolicyValidator`:

```python
APPROVED_COMMAND_SPECS = {
    "dns_lookup": ["dig", "+short", "{record_type}", "{target}"],
    "whois_lookup": ["whois", "{target}"],
    "metadata_extractor": ["exiftool", "-json", "{file_path}"],
    "subdomain_enum": ["subfinder", "-d", "{domain}", "-silent"],
    "cert_inspector": ["openssl", "s_client", "-connect", "{target}:443"],
}
```

### Injection Defense
- Shell metacharacters are strictly forbidden: `;`, `&`, `|`, `` ` ``, `$`, `>`, `<`, `\n`, `\r`, `(`, `)`.
- Arguments must conform to strict regex patterns (e.g. valid hostnames, domains, or safe alphanumeric flags).
- Commands are passed to the container as argument vectors (exec arrays), bypassing any intermediate `/bin/sh -c` shell parser.

---

## 5. Terminal Worker Architecture

The Terminal Head coordinates 4 specialized execution workers:

1. **CLI OSINT Worker**: Runs approved OSINT tools (e.g. subfinder, whois).
2. **Network Intelligence Worker**: Performs DNS records, certificates, and IP route discovery.
3. **Metadata Analysis Worker**: Extracts file metadata (EXIF, PDF metadata, timestamps) without altering target assets.
4. **File & Document Processing Worker**: Safely parses text, logs, and document structures.

---

## 6. Real-Time Terminal Observability

- Real-time logging records `stdout`, `stderr`, `exit_code`, and `duration_ms` in `terminal_execution_logs`.
- The Terminal Control Center frontend (`/terminal`) provides an interactive console viewer with color-coded status, syntax highlighting, and manual command dispatch for authorized investigators.

