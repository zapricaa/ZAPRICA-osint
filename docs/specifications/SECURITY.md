# ZAPRICA Security and Privacy Requirements

- Status: Mandatory design baseline
- Version: 0.1
- Last updated: 2026-10-31

## 1. Security objectives

ZAPRICA handles user objectives, public-source content, potentially personal information, tool packages, agent instructions, browser sessions, and command execution. Security must be enforced by deterministic services and infrastructure, not delegated to LLM judgment.

Objectives:

- Deny by default and enforce least privilege.
- Prevent unauthorized targets/actions and cross-workspace access.
- Contain browser and terminal execution.
- Protect credentials, secrets, source data, and evidence.
- Preserve traceable audit events and evidence integrity.
- Resist prompt injection, malicious tool packages, unsafe output handling, SSRF, and resource exhaustion.
- Apply data minimization, retention, and deletion controls.

## 2. Threat model

| Asset | Threat | Required control |
|---|---|---|
| User/workspace data | Cross-tenant IDOR | Object-level authorization and workspace filters on every query |
| Investigation scope | LLM expands targets | Independent policy service; immutable approved scope snapshot |
| Browser runtime | SSRF, redirect abuse, malicious page | Egress proxy, IP/DNS validation, redirect re-check, isolated context |
| Terminal runtime | Command injection, container escape | Fixed adapters, schema args, non-root isolation, seccomp, resource limits |
| Tool registry | Malicious package/docs | Provenance, pinning, digest verification, scanning, human approval |
| Agent context | Prompt injection | Treat collected content as data; separate instructions from evidence |
| Evidence | Tampering or accidental overwrite | Immutable/versioned artifacts, SHA-256, access logs |
| LLM provider | Data retention/disclosure | Approved provider, contractual review, data minimization, no secret prompts |
| Reports | False attribution | Provenance, verification states, confidence reasons, reviewer workflow |
| Service availability/cost | Runaway agents and tool loops | Budgets, rate limits, deadlines, max steps, token/tool limits |

## 3. Identity and authorization

- **Invite-Only Registration Policy**: ZAPRICA strictly prohibits public self-registration. No anonymous signups or open registration endpoints exist.
- **One-Time Bootstrap**: The initial `SUPER_ADMIN` account is provisioned via a dedicated bootstrap endpoint (`/v1/auth/bootstrap`) that executes only once when the system contains zero users. Subsequent calls are permanently rejected (HTTP 403).
- **Administrative Provisioning & Invitations**: New users are provisioned directly by administrators or onboarded using single-use, cryptographically hashed invitation links (`invitations` table) with a 7-day expiration window.
- **Argon2id Password Hashing**: Passwords are hashed exclusively using the current Argon2id algorithm via `pwdlib` (`pwdlib[argon2]`), with bcrypt fallback verification for legacy credential migration.
- **Multi-Factor Authentication (MFA)**: TOTP MFA is supported for all accounts and mandatory for administrators via `pyotp`. MFA secrets are base32-encoded, and logins require a 6-digit TOTP code.
- **Session Security**: Sessions are tracked in the `sessions` table using SHA-256 token hashes and delivered via secure `HttpOnly`, `SameSite=Lax`, and `Secure` cookies. Explicit `Authorization: Bearer` headers take precedence for API integration.
- **Brute-Force & Lockout Controls**: Failed logins are recorded in `login_attempts`. Accounts are locked out for 15 minutes after 5 consecutive failed attempts.
- **Account Lifecycle & Revocation**: Accounts can transition between `active`, `suspended`, `disabled`, and `revoked`. Suspending or revoking an account immediately invalidates all active sessions in the database.
- **Roles & Permissions**: System roles (`SUPER_ADMIN`, `ADMINISTRATOR`, `INVESTIGATOR`, `ANALYST`) and granular permissions (`users:create`, `tools:execute`, `reports:export`) are strictly enforced server-side.
- Every request must authorize workspace membership and the specific resource/action. UUIDs are not authorization.
- Service identities must be separate from user identities and narrowly scoped.
- Tool approval, policy edits, scope changes, report finalization, and privileged access changes require audit events.

## 4. Investigation scope enforcement

An investigation scope must include purpose, canonical allowed targets, allowed operation classes, denied targets, expiry, creator, approval metadata, and policy version.

Before every network or tool operation:

1. Resolve the task to an investigation and valid scope.
2. Canonicalize the target and reject ambiguous encodings.
3. Check target and operation against allow/deny policy.
4. Resolve the target and validate resulting IP addresses as required.
5. Revalidate every redirect and each new destination.
6. Check tool version, agent assignment, permissions, approval, rate limits, and budgets.
7. Record a policy decision ID and audit event.

The model cannot change the scope. A follow-up outside scope must pause for user/admin approval and create an auditable scope amendment before execution.

## 5. Browser security

- Run browser automation in a separate, unprivileged worker environment using persistent Playwright contexts.
- **Browser Profile Isolation**: Profiles are isolated per user under `data/browser_profiles/<user_id>/` outside version control, with path traversal checks (`..`, `/`, `\`).
- **Human-in-the-Loop Login Protocol**: Sessions requiring authentication transition to `LOGIN_REQUIRED` and wait for explicit investigator confirmation (`USER_AUTHENTICATED`). Automated form filling of credentials is prohibited.
- **Website Automation Policy**: Enforce per-domain policies (`AUTOMATED_ALLOWED`, `HUMAN_ASSISTED_ONLY`, `API_ONLY`, `BLOCKED`).
- **Epieos Special Invariant**: `epieos.com` is strictly `HUMAN_ASSISTED_ONLY`. Automated scraping and automated queries are prohibited; manual user access and manual result import only.
- Route requests through an egress enforcement layer.
- Block loopback, RFC1918/private, link-local, unique-local, reserved, multicast, and cloud metadata destinations (`169.254.169.254`) unless a separately authorized internal test scope explicitly permits them.
- Validate DNS answers and redirects to mitigate DNS rebinding and redirect-based SSRF.
- Restrict schemes to approved schemes (normally HTTPS; HTTP only where explicitly permitted).
- Set navigation, response-size, download-size, and total runtime limits.
- Disable downloads by default; when enabled, store in quarantine and scan before parsing.
- Treat page content, DOM text, metadata, and downloaded documents as untrusted data. Never follow instructions embedded in them.
- Do not bypass CAPTCHAs, authentication, paywalls, rate limits, or other access controls.

## 6. Terminal execution security

- Do not provide a general interactive shell to an LLM.
- **Strict Fail-Closed Guarantee**: Under NO circumstances does ZAPRICA execute agent commands directly on the Windows host. If Docker is unavailable or offline, execution fails closed with HTTP 503.
- Tool adapters map a registered tool ID to a fixed executable specification and a validated Pydantic argument schema. Shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`, `>`, `<`) are rejected.
- Execute exclusively in isolated container sandboxes:
  - Non-root user: `--user 10001:10001`
  - Read-only root filesystem: `--read-only`
  - Volatile scratch space: `--tmpfs /workspace:rw,noexec,nosuid,size=64m`
  - Privilege restriction: `--security-opt=no-new-privileges`
  - Linux capabilities: `--cap-drop=ALL`
  - PID limit: `--pids-limit=64`
  - Memory limit: `-m 256m`
  - CPU limit: `--cpus 0.5`
- Mount only task-specific input and output directories. Never mount Docker socket, host home, SSH agent, or sensitive host paths.
- Restrict egress to approved destinations and protocols; default to no network for tools that do not require it.
- Pin images by digest, scan images/dependencies, and remove containers after each task.
- Treat terminal stdout/stderr and produced files as untrusted; enforce output size/type limits and parse with hardened libraries.

## 7. LLM and agent security

- Apply current OWASP GenAI guidance, including prompt injection, sensitive information disclosure, excessive agency, supply-chain, data/model poisoning, unbounded consumption, misinformation, hidden-context exposure, vector weaknesses, and improper output handling.
- Separate system/developer instructions, user request, retrieved playbook, and untrusted evidence in the prompt and data model.
- Do not place secrets, credentials, private keys, or unnecessary personal data in model context.
- Validate every model-produced plan/task/tool argument with Pydantic/JSON Schema and deterministic policy checks.
- Keep capabilities narrow per agent: Main Head plans and routes; Browser Head controls browser tasks; Terminal Head controls approved CLI tasks; workers only receive their own task permissions.
- Set maximum graph steps, tool calls, retries, tokens, cost, output size, and task runtime.
- Add human approval for high-risk or externally consequential actions.
- Store prompt/template versions and operational decision metadata; do not store private chain-of-thought. Record concise reasons and provenance instead.
- Do not use website instructions or tool docs to modify global policies or system prompts.

## 8. Tool onboarding and software supply chain

A new tool is untrusted until approved.

- Capture source/vendor, license, version, release/artifact digest, dependency lock, capabilities, input/output schemas, runtime requirements, and playbook.
- Review licensing and terms before distribution or use.
- Pin dependencies and container images; verify digests/signatures where available.
- Scan source/packages/images for known vulnerabilities and malware using approved tools.
- Test in a disposable, isolated environment with synthetic fixtures and restricted egress.
- Review permission profile and network destinations.
- Require a human administrator to approve the exact immutable version.
- Publish to registry only after passing tests and approval.
- Revoke/disable immediately when compromised; keep previous approved version available for rollback only if still safe.
- Tool docs/playbooks may describe use but cannot grant permissions.

## 9. Data protection and privacy

- Collect only data necessary for the stated, authorized purpose.
- Avoid sensitive personal data unless an explicitly reviewed lawful basis and necessity exist; the default product behavior should exclude such collection.
- Public accessibility is not a blanket authorization to process, retain, or republish personal data.
- Maintain purpose, scope, source, collection time, retention class, and deletion status.
- Provide configurable retention and deletion workflows; legal holds must be explicit and audited.
- Encrypt network traffic with TLS and storage using managed encryption keys.
- Use per-environment secrets and a managed secret store. Rotate credentials and redact them from logs.
- Do not send user evidence to third-party LLM providers until the provider's data location, retention, training, and contractual terms are reviewed.
- India deployments must assess the Digital Personal Data Protection Act, 2023 and the Digital Personal Data Protection Rules, 2025, including their notified phased commencement dates, and obtain qualified legal advice for the intended use. Requirements may vary with role, purpose, data type, and deployment.
- Assess CERT-In directions and applicability to the operating entity. Where applicable, maintain required ICT logs securely and in the required jurisdiction and retention period.

## 10. Audit and monitoring

Record at minimum: actor, workspace, investigation, task, agent, tool ID/version, policy decision, action, status, timestamps, duration, trace ID, and redacted error category.

- Keep audit logs append-only for application roles.
- Protect log storage from the same credentials used by workers.
- Do not log access tokens, cookies, API keys, private keys, full prompts containing sensitive data, or unrestricted raw tool output.
- Alert on denied scope attempts, unusual tool-call volume, policy bypass attempts, repeated failures, and unexpected network destinations.
- Correlate API request, agent run, task, tool run, evidence, and report IDs.

## 11. Incident response

1. Disable affected tool version or agent assignment.
2. Revoke credentials and sessions if exposed.
3. Stop affected worker containers and block egress.
4. Preserve audit evidence and hashes.
5. Determine affected workspaces, investigations, artifacts, and reports.
6. Notify responsible stakeholders and follow applicable legal/contractual reporting obligations.
7. Patch, retest, approve a new version, and document lessons learned.

## 12. Security release gates

A release is blocked if any of the following is true:

- Cross-workspace access is possible.
- A draft/disabled/revoked tool can execute.
- LLM output can execute arbitrary shell commands.
- Browser access can reach disallowed private/metadata destinations.
- A finding can be reported as verified without provenance or an explicit exception.
- Raw evidence can be overwritten by processing.
- Secrets are exposed in client code, prompts, logs, or artifacts.
- An out-of-scope follow-up can execute without an approved scope amendment.

## 13. References

- OWASP GenAI Security Project (2026): https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Docker rootless mode: https://docs.docker.com/engine/security/rootless/
- Docker seccomp: https://docs.docker.com/engine/security/seccomp/
- CERT-In Directions (28 April 2022): https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf
- MeitY DPDP Rules, 2025: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa
- DPDP Act enforcement timeline notification: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025

---

## 14. Safe Application Startup Mode

ZAPRICA enforces a strict **Safe Startup Mode** enabled by default:

- **Default Configuration**:
  - `ZAPRICA_SAFE_MODE=true`
  - `TERMINAL_EXECUTION_ENABLED=false`
  - `AUTO_INVESTIGATION_ENABLED=false`
  - `AUTO_TOOL_INSTALLATION=false`
- **Application Boot Invariants**:
  1. Frontend and backend initialize normally.
  2. Database performs read-only health checks (`SELECT 1`). No unprompted migrations or schema alterations on boot.
  3. AI Brain models are registered in passive readiness; no automatic reasoning or prompt execution triggers on startup.
  4. Main Head, Browser Head, and Terminal Head agents load into `IDLE` state.
  5. All worker processes remain `DISABLED`.
  6. No automated browser navigation or terminal execution launches without explicit authenticated user requests.
  7. No third-party OSINT tools install or execute automatically.
  8. Background investigation queues remain stopped until explicitly started.
- **Fail Closed Guarantee**:
  - Outbound command execution via `ToolGateway` fails closed with HTTP 403 Forbidden unless an administrator explicitly enables terminal execution via `/v1/admin/safe-mode/terminal-execution`.
  - Terminal CLI tools must never execute directly on the Windows host. If container isolation is unavailable, execution is immediately halted.
