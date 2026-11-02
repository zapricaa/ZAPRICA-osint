# ZAPRICA — Security & Isolation Audit Report

**Date**: 2026-11-02  
**Auditor**: Principal DevSecOps & Application Security Architect  
**Scope**: Dedicated Browser & Terminal Agent Environments, Isolation Boundaries, Host Protections, RBAC, and Safe Mode  
**Overall Finding**: SECURE — NO CRITICAL OR HIGH VULNERABILITIES IDENTIFIED  

---

## 1. Executive Summary

A comprehensive security audit of ZAPRICA was conducted following the implementation of dedicated environments for the Browser Head Agent and Terminal Head Agent. The audit focused on host protection, network egress restriction, privilege containment, prompt injection defense, and authentication verification.

---

## 2. Threat & Vulnerability Assessment

### 2.1 Windows Host Protection & Command Injection
- **Finding**: PASS
- **Analysis**: The Terminal Head Agent and its workers NEVER execute commands directly on the host operating system (`cmd.exe`, `powershell.exe`, or Windows subprocesses).
- **Control**:
  - The `DockerSandboxManager` executes commands exclusively in disposable Docker containers.
  - The `TerminalExecutionPolicyValidator` disallows all shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`, `>`, `<`, `\n`, `\r`, `(`, `)`).
  - All commands are invoked as raw argument vectors, bypassing `/bin/sh -c`.
  - **Fail-Closed Guarantee**: If the Docker daemon is unreachable or the container cannot be instantiated, the application returns HTTP 503 Service Unavailable. Falling back to the Windows host is strictly blocked by code invariants.

### 2.2 Container Sandbox Security & Capabilities
- **Finding**: PASS
- **Analysis**: Container sandboxes are hardened against breakout and resource exhaustion.
- **Enforced Flags**:
  - `--read-only`: The container root filesystem is strictly read-only.
  - `--tmpfs /workspace:rw,noexec,nosuid,size=64m`: In-memory workspace without persistent disk state.
  - `--user 10001:10001`: Unprivileged non-root execution.
  - `--security-opt=no-new-privileges`: Preempts setuid privilege escalation.
  - `--cap-drop=ALL`: Drops all Linux kernel capabilities.
  - `--pids-limit=64`: Preempts fork bombs.
  - No sensitive host mounts: Docker socket `/var/run/docker.sock`, Windows drives `C:\`, `E:\`, and user home directories are strictly prohibited from container mounts.

### 2.3 SSRF & Browser Egress Firewall
- **Finding**: PASS
- **Analysis**: Playwright workers and HTTP requests are shielded by the `BrowserSecurityValidator`.
- **Enforced Checks**:
  - Pre-flight DNS resolution of target hostnames.
  - Strict CIDR blocking against RFC 1918 private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  - Strict blocking of loopback addresses (`127.0.0.0/8`, `::1`).
  - Strict blocking of link-local and cloud metadata addresses (`169.254.169.254`).
  - Real-time interception of navigation redirects via Playwright route hooks, preventing redirect-based SSRF.

### 2.4 Browser Profile & Cookie Isolation
- **Finding**: PASS
- **Analysis**: Browser profiles are segregated by user under `data/browser_profiles/<user_id>/<profile_name>/`.
- **Controls**:
  - Directory traversal defense: Paths containing `..`, `/`, or `\` are caught and rejected with HTTP 400.
  - Cross-user data leakage: User A's session context cannot access User B's profile directory.
  - Git isolation: `data/browser_profiles/` is excluded from git in `.gitignore`.

### 2.5 Website Automation Policies & Epieos Invariant
- **Finding**: PASS
- **Analysis**: `BrowserPolicyEngine` validates all target domains against policy rules.
- **Controls**:
  - Epieos (`epieos.com`) is hard-coded as `HUMAN_ASSISTED_ONLY`. Automated scraping and automated queries are blocked with HTTP 403.
  - Manual user access and manual result import are enforced.
  - Administrators cannot override `epieos` to `browser_automation_allowed=true` (backend rejects with HTTP 400).
  - Prohibited domains (`*.mil`) are blocked by wildcard policy matching.

### 2.6 Human Authentication Confirmation Protocol
- **Finding**: PASS
- **Analysis**: AI agents are prevented from automated form-filling of login credentials, avoiding credential theft and anti-bot trigger locks.
- **Controls**:
  - Interactive login challenges transition to `LOGIN_REQUIRED`.
  - Investigator completes manual authentication in a visible browser.
  - Session resumes only after investigator issues an authenticated POST request to `/confirm-authentication`, generating an immutable `BrowserSessionEvent`.

### 2.7 Safe Startup Invariants
- **Finding**: PASS
- **Analysis**: Application boots in safe mode by default (`ZAPRICA_SAFE_MODE=true`, `TERMINAL_EXECUTION_ENABLED=false`, `AUTO_INVESTIGATION_ENABLED=false`).
- **Controls**:
  - Agents boot in `IDLE` state.
  - Workers boot in `DISABLED` state.
  - No background investigations run automatically.
  - Read-only health checks are executed without modifying the database.

---

## 3. Residual Risks & Recommended Hardening

1. **Host-level Docker Daemon Security**: Ensure the Docker daemon on production Linux servers runs in rootless mode (`dockerd-rootless.sh`) for defense-in-depth.
2. **Container Network Egress**: For CLI OSINT tools that do not require network connectivity (e.g. `exiftool`), explicitly pass `--network none` to the container sandbox.

