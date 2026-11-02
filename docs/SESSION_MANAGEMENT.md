# ZAPRICA — Session Management & Human-in-the-Loop Protocol

## 1. Scope & Objective

This document formalizes session lifecycle controls across ZAPRICA's Browser and Terminal execution environments, focusing on human operator supervision, credential containment, and tamper-resistant state tracking.

---

## 2. Browser Session Lifecycle

A Browser Session represents a dedicated Playwright instance bound to an investigation workspace and an authenticated user.

### State Transitions

```
[STARTING] -> [READY] <----------> [BUSY]
                |
                +-> [LOGIN_REQUIRED]
                          |
                          v
                   [AUTHENTICATING]
                          |
                          v (Investigator Confirms)
                 [USER_AUTHENTICATED] -> [READY]
```

### Session Model Attributes
- `id` (UUID): Unique session identifier.
- `investigation_id` (UUID): Foreign key to the parent investigation workspace.
- `user_id` (UUID): The user who launched the session.
- `profile_name` (string): Isolated profile directory name.
- `status` (BrowserSessionStatus): Current state.
- `current_url` (string): Live URL.
- `last_activity_at` (datetime): Timestamp of latest event.
- `auth_state` (JSON): Session persistence tokens, excluding raw passwords.

### Session Expiry & Auto-Termination
Sessions automatically time out after 30 minutes of inactivity to prevent abandoned browser contexts from consuming system resources or leaving authenticated accounts exposed.

---

## 3. Human Login Flow & Investigator Confirmation

When encountering multi-factor authentication (MFA), CAPTCHA, or authentication challenges:
1. Browser Head detects a login form or receives a 401/403 status.
2. The session transitions to `LOGIN_REQUIRED`.
3. The investigator is notified in the Browser Control Center (`/browser`).
4. The investigator clicks **"Open Login Interface"**, taking manual keyboard and mouse control in a non-headless context.
5. The investigator inputs credentials and completes 2FA.
6. The investigator explicitly clicks **"CONFIRM USER AUTHENTICATED"**.
7. The system logs an immutable audit event (`BrowserSessionEvent`) marking `USER_AUTHENTICATED` with the user ID, timestamp, and target domain.
8. Automation resumes only after this explicit human confirmation.

---

## 4. Terminal Session Lifecycle

Terminal sessions represent authenticated, sandboxed execution contexts inside Docker.

### Execution Constraints
- Maximum execution timeout: 60 seconds (prevents hangs).
- Memory limit: 256MB.
- PIDs limit: 64 processes.
- Execution logging: Every executed tool command, argument list, exit code, duration, standard output, and standard error is written to `terminal_execution_logs`.

---

## 5. Security & Isolation Invariants

1. **No Shared Cookies**: Browser profile directories are partitioned by user ID (`data/browser_profiles/<user_id>/...`). User A cannot read or write User B's cookies or sessions.
2. **No Host Access**: Terminal execution is confined to non-root containers. Docker daemon socket `/var/run/docker.sock` is strictly inaccessible to workers.
3. **Audit Trail**: Every state change generates an event in the audit log table (`audit_logs`) and workspace timeline (`investigation_timelines`).

