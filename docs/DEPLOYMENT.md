# ZAPRICA Deployment and Operations Runbook

- Status: Proposed runbook
- Version: 0.1
- Last updated: 2026-10-31

## 1. Deployment goals

Deploy a secure, reproducible application with separate trust boundaries for the web/API, database, object storage, agent orchestration, browser workers, and terminal workers. The initial environment should be local development; then staging; then a restricted production deployment after security gates pass.

This repository does not yet include application source code, Dockerfiles, CI workflows, or a Compose file. The steps below define the target deployment procedure and must be adapted to the actual implementation.

## 2. Environment topology

### Local

- Next.js development server.
- FastAPI development server.
- PostgreSQL development database.
- Local S3-compatible object store or a dedicated test bucket.
- Optional Redis only if used by implemented features.
- Playwright browser worker in a disposable process/container.
- Terminal sandbox disabled by default; enable only after its image and isolation tests are complete.

### Staging

- Same application image and migration path as production.
- Separate credentials, database, bucket, LLM provider project, and tool registry.
- Synthetic test data only; do not copy production evidence by default.
- Outbound access restricted to explicit test domains and required service endpoints.
- Terminal runtime isolated on separate worker nodes or hardened containers.

### Production

- TLS at the ingress/load balancer.
- Private network for database, object store, and worker services.
- Separate runtime identities and egress policy for browser and terminal workers.
- Managed database/object storage and secret manager where available.
- Centralized protected logs, metrics, alerts, and backups.
- No public route to the tool gateway or worker control plane.

## 3. Configuration and secrets

Maintain an `.env.example` with names and safe dummy values only. Expected configuration categories:

```dotenv
APP_ENV=development
API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg://zaprica:change-me@localhost:5432/zaprica
REDIS_URL=redis://localhost:6379/0
OBJECT_STORE_ENDPOINT=http://localhost:9000
OBJECT_STORE_BUCKET=zaprica-evidence-dev
OBJECT_STORE_ACCESS_KEY=local-only
OBJECT_STORE_SECRET_KEY=local-only
LLM_PROVIDER=disabled
LLM_API_KEY=
JWT_SIGNING_KEY=replace-with-secret-manager-value
LOG_LEVEL=INFO
```

These are illustrative variable names, not production values. Do not commit a real `.env`. In production, use a secret manager or platform secret injection. Rotate secrets and scope them per service.

## 4. Build and release pipeline

Every pull request should run:

1. Secret scanning and dependency/license checks.
2. Python format/lint/type checks and unit tests.
3. Frontend lint/type checks/build/tests.
4. Database migration validation against an ephemeral database.
5. OpenAPI lint/schema validation.
6. Container build and image scan.
7. Integration tests using mock/synthetic tool adapters.
8. Security tests for object-level authorization, prompt injection handling, SSRF controls, and terminal adapter restrictions.

On merge to the release branch:

1. Build immutable frontend, API, and worker images.
2. Tag with commit SHA and release version; record image digests.
3. Generate an SBOM and preserve build provenance.
4. Deploy to staging.
5. Run migrations using a dedicated migration identity.
6. Run smoke and end-to-end tests.
7. Require approval for production deployment.
8. Deploy a canary or a small percentage first where supported.
9. Verify health, errors, task completion, worker sandbox policy, and event delivery.
10. Complete rollout only after the observation window passes.

## 5. Database migration procedure

1. Back up the target database and verify the backup is restorable.
2. Review migration SQL and estimate locks/rewrites.
3. Prefer additive migrations and expand/migrate/contract.
4. Run migration in staging with production-like data volume (synthetic or appropriately protected).
5. Run production migration once using the deployment job, not from every API replica.
6. Verify schema version and application health.
7. Do not automatically run destructive downgrade migrations. Prefer a forward fix unless a tested rollback is safe.

## 6. Rollback runbook

Trigger rollback when health checks fail, error rates rise beyond the release threshold, workers violate policy, evidence integrity checks fail, or critical workflow regressions occur.

1. Stop further rollout and disable new investigation dispatch if integrity/safety is in doubt.
2. Disable the affected tool version or worker capability from the registry.
3. Route traffic to the last known-good application image.
4. Stop incompatible workers and cancel/hold queued tasks as appropriate.
5. Restore compatible schema/application state. Do not roll back a destructive schema change without a verified plan.
6. Preserve logs, traces, artifact digests, and failed task IDs.
7. Verify login, workspace isolation, investigation listing, report viewing, and worker policy enforcement.
8. Re-enable dispatch only after the cause is understood and controls are validated.
9. Record incident, timeline, impact, and corrective actions.

## 7. Backup and recovery

- Enable encrypted PostgreSQL backups and point-in-time recovery according to the selected provider/service.
- Version object storage where supported; use retention/object-lock controls where required by evidence policy.
- Back up tool manifests, approved playbooks, prompt/template versions, and deployment configuration, but keep secrets in the secret manager.
- Test restoration regularly in a separate environment.
- Define and approve RPO/RTO before production; do not invent availability guarantees without testing.

## 8. Monitoring and alerting

Monitor:

- API latency, error rate, authentication failures, and authorization denials.
- Active investigation count and task queue age.
- Agent run duration, retries, timeouts, token/model cost, and tool calls per investigation.
- Browser navigation failures, blocked destinations, downloads, response sizes, and egress denials.
- Terminal container starts, policy denials, resource usage, image digest, and non-zero exits.
- Tool version validation/approval/revocation events.
- Database health, connection pool, storage capacity, artifact hash mismatches, and backup age.
- Audit log delivery and retention health.

Alert on sudden changes, policy violations, expired scopes, repeated worker failures, unusual spend, or evidence-integrity mismatches.

## 9. Production release checklist

- [ ] Threat model and security review approved.
- [ ] All acceptance criteria relevant to the release pass.
- [ ] Admin MFA and RBAC enabled.
- [ ] Secrets stored in a secret manager and rotation tested.
- [ ] Browser egress controls tested against private and metadata destinations.
- [ ] Terminal sandbox tested for privilege, filesystem, network, and resource isolation.
- [ ] Tool versions pinned, scanned, validated, and approved.
- [ ] Retention/deletion policy reviewed for deployment jurisdiction.
- [ ] Database/object storage backups verified.
- [ ] Audit and incident alerting operational.
- [ ] Restore and rollback procedure tested.
- [ ] Operational owner and security contact documented.

## 10. India-specific operational review

Before operating in India, determine the deployment entity's obligations under applicable privacy, cybersecurity, intermediary, contract, and sector-specific requirements. Review the DPDP Act, 2023 and DPDP Rules, 2025 with their notified phased commencement dates, and assess whether CERT-In directions apply to the entity and service model. Do not treat this runbook as legal advice. Check the latest official notifications before production launch.

References:

- MeitY DPDP Rules, 2025: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa
- CERT-In Directions, 28 April 2022: https://cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf
