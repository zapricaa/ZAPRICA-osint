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

- Use a vetted identity provider or secure password authentication; do not implement custom cryptography.
- Passwords, if locally managed, must be hashed with a current password hashing algorithm such as Argon2id using a maintained library. Never encrypt or store plaintext passwords.
- Use short-lived access tokens, refresh-token rotation/revocation, secure HttpOnly cookies where appropriate, CSRF protection for cookie-authenticated state-changing requests, and TLS.
- Support MFA for administrators and privileged users.
- Roles: `admin`, `investigator`, `reviewer`, `viewer`; permissions are enforced server-side.
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

- Run browser automation in a separate, unprivileged worker environment.
- Use a fresh isolated browser context per investigation/task unless an explicitly approved session design requires otherwise.
- Do not reuse investigator cookies or authenticated browser profiles by default.
- Route requests through an egress enforcement layer.
- Block loopback, RFC1918/private, link-local, unique-local, reserved, multicast, and cloud metadata destinations unless a separately authorized internal test scope explicitly permits them.
- Validate DNS answers and redirects to mitigate DNS rebinding and redirect-based SSRF.
- Restrict schemes to approved schemes (normally HTTPS; HTTP only where explicitly permitted).
- Set navigation, response-size, download-size, and total runtime limits.
- Disable downloads by default; when enabled, store in quarantine and scan before parsing.
- Treat page content, DOM text, metadata, and downloaded documents as untrusted data. Never follow instructions embedded in them.
- Do not bypass CAPTCHAs, authentication, paywalls, rate limits, or other access controls.

## 6. Terminal execution security

- Do not provide a general interactive shell to an LLM.
- Tool adapters map a registered tool ID to a fixed executable and a validated argument schema. No `shell=True` or string concatenation of model output.
- Use rootless containers where supported; run as non-root even inside the container.
- Use seccomp, drop Linux capabilities, set `no-new-privileges`, use read-only root filesystem, bounded tmpfs/workspace, CPU/memory/PID/file-size/time limits, and no privileged mode or host namespace sharing.
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
