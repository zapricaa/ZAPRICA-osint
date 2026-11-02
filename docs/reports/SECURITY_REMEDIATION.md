# ZAPRICA — Security Remediation & DevSecOps Audit

**Date**: 2026-11-02  
**Role**: Application Security Engineer & DevSecOps Lead  
**Branch**: `hotfix/phase7-remediation`  
**Classification**: Internal Technical Security Documentation  

---

## 1. Threat Model & Key Security Principles

ZAPRICA handles sensitive open-source intelligence gathering operations across untrusted web domains, network targets, and automated tools. The core security architecture enforces five defense-in-depth invariants:

1. **Invite-Only / Strict Authentication Barrier**: Zero public registration, timing-safe one-time bootstrap secret protection, and mandatory MFA.
2. **Strict Fail-Closed Invariant**: Host execution is strictly prohibited under all circumstances. If the Docker sandbox or Playwright isolated context is unavailable, operations fail closed with explicit HTTP 503 errors.
3. **SSRF Egress Enforcement**: Defense against internal network probing, link-local addresses, and cloud metadata theft at both DNS/IP resolution and Playwright route-level interception layers.
4. **Agent Isolation & Bounded Capabilities**: AI agents propose actions via structured Pydantic schemas; they cannot bypass RBAC, access host resources, or override tool execution permissions.
5. **Human-in-the-Loop Safeguards**: Sensitive actions (e.g. Epieos OSINT and account logins) are marked `HUMAN_ASSISTED_ONLY` with manual investigator authentication required.

---

## 2. In-Depth Security Remediation Breakdown

### 2.1 Remediation: Bootstrap Secret Timing-Safe Validation (CWE-306, CWE-208)

- **Vulnerability**: Prior to remediation, the `/v1/auth/bootstrap` endpoint only checked `if user_count == 0:`. Any external attacker who reached the service first could register as the global `SUPER_ADMIN` without proving authorization or ownership of the deployment environment. Furthermore, any secret comparison risked timing attack side-channels.
- **Remediation**:
  - Added `BOOTSTRAP_SECRET` to `Settings` (configured via `ZAPRICA_BOOTSTRAP_SECRET` environment variable).
  - Enforced constant-time HMAC validation using Python's `hmac.compare_digest(data.bootstrap_secret.strip(), settings.BOOTSTRAP_SECRET.strip())`.
  - Rejection with HTTP 403 occurs before querying or mutating user records if the secret is incorrect.
  - Added unit test coverage verifying that invalid bootstrap secrets fail with HTTP 403, and subsequent bootstrap calls fail with HTTP 409.

### 2.2 Remediation: Playwright Route-Level SSRF Interception (CWE-918)

- **Vulnerability**: Initial SSRF checks only validated the target URL supplied in the request body. If the destination domain performed an HTTP 302 redirect to `http://169.254.169.254` (cloud metadata service) or `http://127.0.0.1:8000/internal`, or loaded malicious iframes/subresources, the Playwright browser engine could access restricted network resources.
- **Remediation**:
  - Configured route-level interception on the Playwright `BrowserContext`:
    ```python
    async def _route_ssrf_interceptor(route):
        req_url = route.request.url
        if req_url.startswith(("data:", "blob:", "about:")):
            await route.continue_()
            return
        try:
            BrowserSecurityValidator.validate_target_url(req_url)
            await route.continue_()
        except Exception as ssrf_err:
            logger.warning("SSRF filter blocked request to %s: %s", req_url, ssrf_err)
            await route.abort("blockedbyclient")

    await context.route("**/*", _route_ssrf_interceptor)
    ```
  - Resolves all hostnames, inspects all resolved IP addresses against 18 restricted CIDR ranges (RFC 1918, RFC 3927 link-local, loopback, CGNAT, broadcast), and aborts prohibited requests before the network socket connects.

### 2.3 Remediation: Elimination of Synthetic Fallback & Host Execution Defense (CWE-250, CWE-393)

- **Vulnerability**: If Docker CLI was absent on the server host, the terminal execution service previously fell back to `_deterministic_fallback_execution`, which synthesized hardcoded responses (`93.184.216.34`). This created false evidence trails and masked infrastructure failures.
- **Remediation**:
  - Completely purged the `_deterministic_fallback_execution` method and all synthetic mock helpers from production code.
  - Enforced strict fail-closed assertion:
    ```python
    if not DockerSandboxManager.is_docker_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fail-Closed Security Invariant: Docker sandbox is offline and terminal execution is strictly isolated. Host execution is prohibited."
        )
    ```
  - Guaranteed that agent commands are never executed directly on the host operating system (Windows or Linux).

### 2.4 Remediation: Object-Level Authorization (IDOR) Protection (CWE-639)

- **Vulnerability**: Browser sessions and terminal tasks accepted UUID parameters without verifying that the requesting authenticated user was either the resource creator or an assigned investigator in the same workspace.
- **Remediation**:
  - Implemented `_verify_session_ownership(session_id, current_user)` in `app/api/v1/browser.py`.
  - Applied across `/sessions/{id}`, `/navigate`, `/confirm-authentication`, `/screenshot`, `/import-manual-result`, and `/stop`.
  - Implemented workspace membership verification and audit logging in `app/api/v1/terminal.py` before executing tasks or querying terminal container logs.

---

## 3. Verification & Compliance Sign-Off

All remediations have been verified by automated regression test suites and manual validation. The platform adheres strictly to zero-trust architecture principles and is cleared for controlled integration testing.

