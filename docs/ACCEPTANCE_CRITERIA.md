# ZAPRICA Acceptance Criteria

- Status: Draft test specification
- Version: 0.1
- Last updated: 2026-10-31

Use these scenarios as executable acceptance tests. IDs should be referenced in pull requests and release notes.

## Feature 1 — Identity and workspace authorization

### AC-AUTH-01: Unauthenticated user cannot access investigations

**Given** a request has no valid authentication credential  
**When** it calls a protected investigation endpoint  
**Then** the API returns `401` and no investigation data is disclosed.

### AC-AUTH-02: User cannot read another workspace's investigation

**Given** user A belongs to workspace A and investigation B belongs to workspace B  
**When** user A requests investigation B by ID  
**Then** the API returns `404` or a consistently documented non-disclosing denial and records the security event.

### AC-AUTH-03: Viewer cannot start an investigation

**Given** a user has only the `viewer` role  
**When** the user calls the start endpoint  
**Then** the API returns `403` and no task is dispatched.

### AC-AUTH-04: Admin action is audited

**Given** an administrator approves a tool version  
**When** the approval is committed  
**Then** an append-only audit event records the actor, tool/version, decision, timestamp, and trace ID.

## Feature 2 — Investigation creation and scope

### AC-INV-01: Create investigation with scope

**Given** an authenticated investigator has workspace access  
**And** the request contains a valid purpose, allowed target, operations, and expiry  
**When** the investigator creates an investigation  
**Then** the API stores the investigation and scope in a non-executing state.

### AC-INV-02: Reject empty or malformed scope

**Given** an investigation request has no allowed targets or an invalid target format  
**When** the request is submitted  
**Then** validation fails and no external task is created.

### AC-INV-03: Enforce scope at execution time

**Given** an investigation scope allows `example.org` only  
**When** a worker attempts to access an unrelated target  
**Then** the policy service denies the operation before network access and records the denial.

### AC-INV-04: Scope expiry stops new work

**Given** the investigation scope has expired  
**When** a new task is dispatched or a paused task is resumed  
**Then** the policy service blocks execution until a valid scope is approved.

## Feature 3 — Main Head planning and routing

### AC-MAIN-01: Main Head creates typed plan

**Given** a valid website intelligence request  
**When** Main Head plans the investigation  
**Then** it produces schema-valid tasks with capability, target, scope reference, permitted tools, expected output, budget, deadline, and risk class.

### AC-MAIN-02: Browser task routes to Browser Head

**Given** a task requires approved browser capabilities  
**When** Main Head dispatches it  
**Then** the task is assigned to Browser Head and not directly to a terminal worker.

### AC-MAIN-03: Terminal task routes to Terminal Head

**Given** a task requires an approved CLI capability  
**When** Main Head dispatches it  
**Then** the task is assigned to Terminal Head and runs only through the terminal gateway.

### AC-MAIN-04: LLM cannot expand scope

**Given** the model proposes a target outside the approved scope  
**When** the plan is validated  
**Then** the task is rejected or paused for a human-approved scope amendment.

## Feature 4 — Sub-Head and worker reporting

### AC-AGENT-01: Worker reports to its own Sub-Head

**Given** Browser Head assigns a task to a browser worker  
**When** the worker completes, finds nothing, or fails  
**Then** it returns a typed status and result to Browser Head.

### AC-AGENT-02: Sub-Head returns findings package to Main Head

**Given** Browser Head has reviewed worker results  
**When** its task group completes  
**Then** it returns a versioned findings package, execution status, evidence references, warnings, and failures to Main Head.

### AC-AGENT-03: No findings is not failure

**Given** a worker executed successfully but found no relevant record  
**When** it returns its result  
**Then** status is `no_findings` (or equivalent outcome) and not `failed`.

### AC-AGENT-04: Partial failure is visible

**Given** two workers succeed and one worker times out  
**When** the Sub-Head prepares its package  
**Then** successful findings are returned with a `partial` status and the timeout is visible.

## Feature 5 — Evidence and processing

### AC-EVD-01: Raw evidence is immutable

**Given** a worker stores a raw artifact  
**When** a processing worker normalizes or deduplicates the data  
**Then** the original artifact remains unchanged and derived records reference it.

### AC-EVD-02: Finding has provenance

**Given** a finding is included in a report  
**When** the report is generated  
**Then** the finding has at least one evidence/source reference or an explicit reviewed provenance exception.

### AC-EVD-03: Duplicate processing is deterministic

**Given** the same input evidence and processor version are supplied twice  
**When** deduplication runs  
**Then** the normalized output is stable and the originals remain available.

### AC-EVD-04: Conflicting sources are not silently merged

**Given** two sources provide conflicting values for the same candidate attribute  
**When** Main Head correlates them  
**Then** the conflict and both source references remain visible for review.

## Feature 6 — Tool onboarding (TIMS)

### AC-TIMS-01: New tool starts as draft

**Given** an administrator registers a new tool  
**When** the draft is saved  
**Then** the tool is not executable and is marked `draft`.

### AC-TIMS-02: Documentation is converted to draft playbook

**Given** an administrator supplies tool documentation  
**When** the documentation analyzer extracts usage instructions  
**Then** the result is marked draft/untrusted and cannot change global policies or permissions.

### AC-TIMS-03: Tool version must pass isolated validation

**Given** a tool version is submitted for validation  
**When** tests run  
**Then** they run in an isolated environment with synthetic fixtures and restricted egress, and produce a recorded result.

### AC-TIMS-04: Approval is separate from validation

**Given** automated tests pass  
**When** no administrator has approved the exact version  
**Then** the tool remains unavailable to agents.

### AC-TIMS-05: Only assigned agents discover the tool

**Given** a tool is published for Browser Head only  
**When** Terminal Head requests capability discovery  
**Then** the registry does not return that tool as executable for Terminal Head.

### AC-TIMS-06: Revocation blocks execution

**Given** a tool version is revoked  
**When** an agent attempts to invoke it  
**Then** the gateway denies execution before launching the tool.

### AC-TIMS-07: Version update is immutable

**Given** an approved version exists  
**When** its instructions or adapter change  
**Then** a new version is created and must pass validation and approval again.

## Feature 7 — Execution security

### AC-SEC-01: Arbitrary shell text is rejected

**Given** an agent proposes a raw shell command instead of a registered tool ID and schema-valid arguments  
**When** the tool gateway receives the request  
**Then** it rejects the request and does not start a process.

### AC-SEC-02: Browser cannot reach a private address

**Given** a public target redirects to loopback, private, link-local, or cloud metadata address space  
**When** the browser worker follows the redirect  
**Then** the egress policy blocks it and logs the policy decision.

### AC-SEC-03: Prompt injection is treated as data

**Given** a collected webpage contains text instructing the agent to ignore prior rules or disclose secrets  
**When** the page is processed  
**Then** the content is stored/analysed as untrusted evidence and no privileged action is performed.

### AC-SEC-04: Resource limits stop runaway work

**Given** a worker exceeds its maximum runtime, tool-call count, or output limit  
**When** the limit is reached  
**Then** execution is stopped or cancelled, a bounded failure is recorded, and no unbounded retry occurs.

## Feature 8 — Reporting and user delivery

### AC-REPORT-01: Report distinguishes evidence from inference

**Given** findings include observed facts and inferred relationships  
**When** the report is generated  
**Then** observed facts, inferences, confidence, and limitations are clearly distinguished.

### AC-REPORT-02: Report includes source provenance

**Given** a report contains a finding  
**When** a reviewer opens the report  
**Then** the source/evidence reference and collection time can be inspected, subject to authorization.

### AC-REPORT-03: Incomplete investigation is not presented as complete

**Given** one Sub-Head reports a partial result or required task has failed  
**When** the report is generated  
**Then** the report indicates the incomplete status and limitations.

### AC-REPORT-04: Export is authorized

**Given** a user has no access to an investigation  
**When** the user requests its JSON/CSV/report export  
**Then** no content or artifact URL is returned.

## Feature 9 — Dedicated Browser Environment

### AC-BROWSER-01: Browser profile directory isolation outside git
**Given** an investigator launches a browser session  
**When** the profile directory is created  
**Then** it is stored in `data/browser_profiles/<user_id>/` outside version control, and path traversal strings (`..`, `/`, `\`) are strictly rejected with HTTP 400.

### AC-BROWSER-02: Human login confirmation protocol
**Given** a browser session encounters a login or authentication challenge  
**When** the session transitions to `LOGIN_REQUIRED` and `AUTHENTICATING`  
**Then** automated actions are paused until an authenticated investigator explicitly submits `confirm-authentication`, transitioning to `USER_AUTHENTICATED`.

### AC-BROWSER-03: Website automation policy enforcement
**Given** a target domain is configured with an automation policy (`AUTOMATED_ALLOWED`, `HUMAN_ASSISTED_ONLY`, `API_ONLY`, `BLOCKED`)  
**When** an automated action is proposed  
**Then** the policy engine enforces the allowed actions and rejects prohibited operations with HTTP 403.

### AC-BROWSER-04: Epieos special handling
**Given** the target domain is `epieos.com` or tool is `epieos`  
**When** any automated querying or scraping is attempted  
**Then** it is strictly prohibited (`HUMAN_ASSISTED_ONLY`), and data entry is permitted solely via manual operator access and manual result import.

## Feature 10 — Dedicated Terminal Container Sandbox

### AC-TERMINAL-01: Container sandbox isolation
**Given** a terminal command is approved for execution  
**When** the container is launched  
**Then** it runs non-root (`10001:10001`), with read-only rootfs, tmpfs `/workspace`, dropped Linux capabilities, and no host Docker socket mounted.

### AC-TERMINAL-02: Command allowlist and argument injection defense
**Given** an agent proposes a terminal task  
**When** the command spec or arguments contain shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`) or unapproved binaries  
**Then** the execution policy validator rejects the task before container dispatch.

### AC-TERMINAL-03: Strict fail-closed guarantee
**Given** Docker daemon is offline or container sandbox initialization fails  
**When** a terminal command execution is requested  
**Then** the system fails closed with HTTP 503, strictly prohibiting fallback execution on the host operating system.
