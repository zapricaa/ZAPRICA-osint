# Product Requirements Document (PRD)

- Product: ZAPRICA
- Document status: Draft for engineering review
- Version: 0.1
- Last updated: 2026-10-31
- Owner: Product / Engineering

## 1. Product summary

ZAPRICA is an AI-assisted OSINT investigation workspace. An investigator submits an objective and an explicitly bounded, authorized scope. A central Main Head Agent plans work and delegates it to two specialist supervisors: a Browser Head Agent and a Terminal Head Agent. Each Sub-Head manages workers and returns structured findings packages. The Main Head consolidates, checks, correlates, and presents useful findings with source provenance and limitations.

ZAPRICA must be tool-extensible. An administrator can introduce a future investigation tool through the Tool Intelligence & Management System (TIMS): register its metadata, documentation, capability manifest, adapter, permissions, test it in isolation, review it, approve it, version it, and assign it to eligible agents. Tool onboarding must not require rewriting the Main Head or existing Sub-Heads.

## 2. Problem and opportunity

OSINT investigations often involve separate browser research, command-line utilities, manual data cleanup, repeated records, fragmented evidence, and inconsistent reporting. ZAPRICA aims to provide one controlled workflow with clear task ownership, repeatable processing, traceable evidence, and a coherent report.

## 3. Product goals

1. Provide a clear interface for creating, monitoring, and reviewing authorized investigations.
2. Keep the Main Head Agent as the central planner, dispatcher, supervisor, and final synthesizer.
3. Separate browser and terminal execution responsibilities through two Sub-Heads.
4. Support specialist workers without requiring an LLM for deterministic data-processing tasks.
5. Preserve raw evidence and link every processed finding to its sources and transformations.
6. Allow administrators to onboard, test, approve, version, disable, and assign tools.
7. Enforce authorization, isolation, auditability, privacy, and human approval at system boundaries.
8. Produce readable reports with confidence/verification state, source references, collection times, and known limitations.

## 4. Non-goals and prohibited capabilities

ZAPRICA is not intended to:

- Obtain unauthorized access to accounts, systems, networks, or restricted data.
- Steal credentials, bypass access controls, evade detection, establish persistence, deploy malware, or exploit vulnerabilities.
- Perform indiscriminate collection, profiling, or enrichment of sensitive personal information.
- Make identity claims from weak correlations or present model-generated speculation as verified fact.
- Treat content found online as trusted instructions for agents.
- Execute arbitrary shell commands or arbitrary uploaded code because an LLM requested it.
- Replace legal review, human judgment, or source verification.

## 5. Users and roles

| Role | Responsibilities |
|---|---|
| Administrator | Manage users/roles, approve tools and versions, configure policies, review audit events. |
| Investigator | Create and monitor investigations within assigned permissions; review findings and reports. |
| Reviewer | Review evidence, approve gated actions, mark findings, and finalize reports where permitted. |
| Read-only viewer | View investigations and reports explicitly shared with them. |
| Service identity | Execute narrowly scoped application tasks using service-to-service credentials. |

Initial deployment may be single-workspace, but the schema and authorization model should support workspace isolation.

## 6. Primary user journey

1. User signs in.
2. User creates an investigation with a target, objective, investigation type, purpose, allowed targets, allowed operations, and retention setting.
3. Backend validates identity, role, request fields, policy, and scope.
4. Main Head analyzes intent and creates a structured plan. Ambiguous/high-impact requests are returned for clarification or human review.
5. Main Head routes approved tasks to Browser Head, Terminal Head, or both.
6. Sub-Heads select only tools that are approved, enabled, assigned to that agent, and allowed by the investigation scope.
7. Workers execute bounded tasks in their dedicated runtime and collect evidence.
8. Processing workers clean, normalize, deduplicate, classify, and sort derived data while preserving original evidence.
9. Each Sub-Head reviews its workers' results and returns a versioned findings package plus task status to Main Head.
10. Main Head merges packages, detects cross-source duplicates, validates provenance, assesses confidence, filters irrelevant/out-of-scope findings, and decides whether more work is required.
11. Main Head creates follow-up tasks within the original scope or pauses for approval/clarification.
12. Report service builds a traceable report. Dashboard displays summary, findings, evidence, limitations, and export options.

## 7. Functional requirements

### 7.1 Identity and access

- FR-AUTH-01: Users must authenticate before accessing investigation data.
- FR-AUTH-02: Every resource query must be scoped to the user's workspace and permissions.
- FR-AUTH-03: Roles must be enforced server-side, not only in the UI.
- FR-AUTH-04: Administrative tool approval and policy changes must be auditable.

### 7.2 Investigation management

- FR-INV-01: Create, list, view, pause, resume, and cancel an investigation subject to role and state rules.
- FR-INV-02: Each investigation must define an explicit scope with allowed targets, allowed operation classes, purpose, and expiry/retention metadata.
- FR-INV-03: A request outside scope must be rejected or paused for review; an LLM cannot expand scope.
- FR-INV-04: Investigation lifecycle states: `draft`, `queued`, `planning`, `running`, `awaiting_approval`, `paused`, `completed`, `failed`, `cancelled`.

### 7.3 Main Head Agent

- FR-MAIN-01: Understand user objective and produce a structured plan with assumptions and questions.
- FR-MAIN-02: Check policy and scope before dispatch.
- FR-MAIN-03: Decompose a plan into typed tasks with target, capability, allowed tools, input schema, output schema, deadline, and risk classification.
- FR-MAIN-04: Route browser tasks to Browser Head and approved command-line tasks to Terminal Head.
- FR-MAIN-05: Monitor status and process worker failures, timeouts, partial results, and retries.
- FR-MAIN-06: Consolidate findings, identify duplicates and conflicts, preserve provenance, and record uncertainty.
- FR-MAIN-07: Replan only within authorized scope; pause for approval when a task needs expanded scope or sensitive operations.
- FR-MAIN-08: Produce a report that distinguishes verified facts, unverified observations, inferences, and missing information.

### 7.4 Sub-Heads and workers

- FR-AGENT-01: Browser Head owns browser worker dispatch and Playwright session policy.
- FR-AGENT-02: Terminal Head owns terminal worker dispatch and sandbox policy.
- FR-AGENT-03: Workers must return a typed result even when no findings are found or execution fails.
- FR-AGENT-04: Workers report to their own Sub-Head; Sub-Heads review and return a findings package to Main Head.
- FR-AGENT-05: Worker capabilities and tool access must be explicitly assigned and limited.
- FR-AGENT-06: Data cleaning, normalization, deduplication, classification, and sorting should be deterministic code where possible.

### 7.5 Evidence and findings

- FR-EVD-01: Preserve raw evidence as immutable/versioned artifacts.
- FR-EVD-02: Each processed finding must reference source evidence, source URL or locator where applicable, collector, timestamps, task, and transformation lineage.
- FR-EVD-03: Store content hashes for artifact integrity checks.
- FR-EVD-04: Support finding statuses such as `unreviewed`, `supported`, `contradicted`, `insufficient_evidence`, and `rejected`.
- FR-EVD-05: Cross-source duplicates and conflicts must be visible to the reviewer.
- FR-EVD-06: Do not infer that two records refer to the same person solely because names or usernames match.

### 7.6 Tool Intelligence & Management System (TIMS)

- FR-TIMS-01: Administrators can create a draft tool record with name, description, version, vendor/source, license, execution type, capability tags, and documentation links.
- FR-TIMS-02: Administrators can add installation, usage, examples, limitations, input/output schemas, dependency, and troubleshooting playbooks.
- FR-TIMS-03: System can generate a draft manifest and documentation summary, but generated content must be reviewed.
- FR-TIMS-04: Each tool must have an adapter implementing a controlled interface; the agent must not call an arbitrary executable directly.
- FR-TIMS-05: New tool versions must be validated in an isolated environment against expected tests and policy constraints.
- FR-TIMS-06: A human administrator must approve a tool version before it can be published.
- FR-TIMS-07: Published tools must be versioned, enabled/disabled, revoked, and rolled back.
- FR-TIMS-08: Tool assignment must specify eligible agent classes, capabilities, scope constraints, permissions, and limits.
- FR-TIMS-09: Agents discover tools by capability and retrieve only the relevant playbook at task time.
- FR-TIMS-10: Tool documentation, package metadata, and output are untrusted data and cannot alter system policy.
- FR-TIMS-11: Tool installations must be pinned and provenance/integrity checked; no automatic install from arbitrary web instructions.

### 7.7 Dashboard and reporting

- FR-UI-01: Dashboard shows active/completed/failed investigations and recent activity.
- FR-UI-02: Investigation workspace shows plan, task graph, agent status, progress events, and approval requests.
- FR-UI-03: Evidence explorer shows raw/processed distinction, source references, timestamps, and verification state.
- FR-UI-04: Reports include executive summary, methodology, findings, source references, confidence/verification notes, scope, and limitations.
- FR-UI-05: Export at least JSON and CSV for MVP; PDF may be added after report layout stabilizes.

## 8. Non-functional requirements

- NFR-01 Security: deny by default; least privilege; isolated execution; auditable administrative actions.
- NFR-02 Traceability: all task state changes, tool runs, and findings must be correlated by IDs.
- NFR-03 Reliability: failed tasks must produce explicit failure states; retries must be bounded and idempotent.
- NFR-04 Performance: the UI should show task status without repeatedly polling at aggressive intervals; use SSE or another documented event mechanism.
- NFR-05 Scalability: workers can be scaled independently from the API; initial implementation can remain a modular monolith.
- NFR-06 Maintainability: typed contracts, API specification, migrations, tests, and documented tool adapters.
- NFR-07 Privacy: minimize personal data, apply retention policies, and support deletion/hold workflows as legally required.
- NFR-08 Cost control: set per-investigation model, token, runtime, and tool-call budgets.
- NFR-09 Availability: application must recover from process restarts without marking unfinished work as successful.
- NFR-10 Accessibility: keyboard-accessible and semantically structured UI.

## 9. MVP scope

### Included

- Authentication and workspace role checks.
- Investigation create/list/detail and explicit scope.
- Main Head plan generation and deterministic policy gate.
- Browser Head with one Playwright worker for allowlisted public website/domain metadata and content extraction.
- Deterministic cleaning, normalization, and deduplication.
- Raw artifact storage plus structured findings in PostgreSQL.
- Sub-Head → Main Head findings package contract.
- Main Head report summary with source references and limitations.
- Basic dashboard, progress events, JSON/CSV export.
- Tool Registry data model and administrator-only draft/approval workflow, initially seeded with a small number of reviewed tools.

### Excluded from MVP

- Broad person profiling or bulk personal-data collection.
- Arbitrary shell execution or automatic execution of user-uploaded code.
- Unrestricted network scanning, exploit modules, credentialed access, stealth, or evasion.
- Fully autonomous tool installation/publishing.
- Large library of specialist workers.
- Temporal orchestration until the workflow warrants it.
- Graph database, vector database, multi-tenant SaaS billing, and advanced analytics.

## 10. Success metrics

- 100% of executed tasks have a valid investigation, task, agent, and policy decision reference.
- 100% of published tool versions have an approved manifest, playbook, adapter, and validation record.
- 100% of findings shown in a report have a source/evidence reference or an explicit reason why provenance is unavailable.
- 0 executions from draft, disabled, revoked, or unassigned tools.
- 0 raw evidence overwritten by a processing operation.
- Task failure, timeout, and no-findings outcomes are clearly distinguished.
- MVP end-to-end scenario completes for a controlled allowlisted website.

## 11. Risks and assumptions

- OSINT data can be incomplete, outdated, misleading, or deliberately poisoned.
- Public accessibility does not automatically grant permission to collect, retain, republish, or profile personal data.
- Websites may contain prompt-injection instructions. Content must be handled as data, not instructions.
- Tool packages and documentation can be malicious or compromised; treat onboarding as a supply-chain process.
- LLM output is probabilistic. Important claims require source inspection and human review.
- Provider availability, pricing, API terms, and laws change; revalidate them before deployment.

## 12. Open decisions before production

- Single-operator deployment or multi-workspace deployment for first release.
- Approved LLM provider(s), data-processing location, and no-training/retention terms.
- Exact retention defaults and deletion/legal-hold policy.
- Supported target types and allowlist policy.
- Whether PDF export belongs in MVP.
- Which tool license and provenance checks are mandatory for each tool category.
