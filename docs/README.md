# ZAPRICA — Documentation, Architecture & Audit Repository

This directory contains all non-application files, technical specifications, architecture diagrams, audit reports, and engineering logs for the ZAPRICA OSINT platform.

---

## Directory Organization

```text
docs/
├── architecture/         # System architecture, multi-agent flows, environments & schemas
├── reports/              # Independent audits, remediation reports, and test verification logs
├── specifications/       # Product requirements, acceptance criteria, security & deployment
└── tracking/             # Engineering development logs, implementation status & technical decisions
```

---

## 1. Architecture & Design (`docs/architecture/`)

- [`UPDATED_ARCHITECTURE.md`](architecture/UPDATED_ARCHITECTURE.md) — 3-tier multi-agent hierarchy specification (Main Head, Browser Head, Terminal Head).
- [`SYSTEM_ARCHITECTURE_FLOW.md`](architecture/SYSTEM_ARCHITECTURE_FLOW.md) — End-to-end data flow, task envelopes, and agent communication pathways.
- [`ARCHITECTURE.md`](architecture/ARCHITECTURE.md) — Foundational system architecture, components, and module breakdown.
- [`DATABASE_SCHEMA.md`](architecture/DATABASE_SCHEMA.md) — Relational schema definition, tables, foreign keys, and indexes.
- [`BROWSER_ENVIRONMENT.md`](architecture/BROWSER_ENVIRONMENT.md) — Dedicated Playwright browser manager, profile isolation, and SSRF filter.
- [`TERMINAL_ENVIRONMENT.md`](architecture/TERMINAL_ENVIRONMENT.md) — Hardened Docker sandbox, command allowlisting, and fail-closed invariants.
- [`SESSION_MANAGEMENT.md`](architecture/SESSION_MANAGEMENT.md) — State machine for investigator sessions, MFA, and human authentication flows.
- [`TOOL_EXECUTION_POLICIES.md`](architecture/TOOL_EXECUTION_POLICIES.md) — TIMS policies, domain automation rules, and Epieos restrictions.
- [`API_SPEC.yaml`](architecture/API_SPEC.yaml) — OpenAPI / Swagger REST API specifications.

---

## 2. Audits, Remediations & Test Reports (`docs/reports/`)

- [`REMEDIATION_REPORT.md`](reports/REMEDIATION_REPORT.md) — Master remediation report documenting fixes for auth, models, graph execution, and Docker sandboxes.
- [`SECURITY_REMEDIATION.md`](reports/SECURITY_REMEDIATION.md) — DevSecOps audit of timing-safe secrets, SSRF route interception, and IDOR defenses.
- [`INTEGRATION_TEST_RESULTS.md`](reports/INTEGRATION_TEST_RESULTS.md) — Automated test verification results (45/45 backend pytest passed, 16/16 frontend routes built).
- [`REMAINING_ISSUES.md`](reports/REMAINING_ISSUES.md) — Release assessment and status matrix (**READY FOR LOCAL TESTING**).
- [`SECURITY_AUDIT.md`](reports/SECURITY_AUDIT.md) — Independent vulnerability assessment and zero-trust verification.
- [`IMPLEMENTATION_REPORT.md`](reports/IMPLEMENTATION_REPORT.md) — Implementation audit of core modules and agent contracts.
- [`TEST_RESULTS.md`](reports/TEST_RESULTS.md) — Historical test execution records across project milestones.
- [`WORK_LOG.md`](reports/WORK_LOG.md) — Chronological work diary of engineering improvements.

---

## 3. Specifications & Governance (`docs/specifications/`)

- [`PRD.md`](specifications/PRD.md) — Product Requirements Document (vision, user personas, MVP scope).
- [`ACCEPTANCE_CRITERIA.md`](specifications/ACCEPTANCE_CRITERIA.md) — Testable Given/When/Then scenarios for all core features.
- [`SECURITY.md`](specifications/SECURITY.md) — Threat model, security boundaries, and authorization controls.
- [`DEPLOYMENT.md`](specifications/DEPLOYMENT.md) — Local development, Docker Compose, and production deployment guide.
- [`CONTRIBUTING.md`](specifications/CONTRIBUTING.md) — Contribution guidelines, branch management, and coding standards.

---

## 4. Development Tracking & Roadmaps (`docs/tracking/`)

- [`DEVELOPMENT_LOG.md`](tracking/DEVELOPMENT_LOG.md) — Detailed engineering history across all development phases.
- [`IMPLEMENTATION_STATUS.md`](tracking/IMPLEMENTATION_STATUS.md) — Feature status tracking and acceptance criteria verification matrix.
- [`TECHNICAL_DECISIONS.md`](tracking/TECHNICAL_DECISIONS.md) — Architectural Decision Records (ADRs) and design rationales.
- [`TODO.md`](tracking/TODO.md) — Operational enhancements and future roadmap items.

