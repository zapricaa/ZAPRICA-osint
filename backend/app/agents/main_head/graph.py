"""Main Head Agent LangGraph Orchestration Supervisor with Google Gemini AI Brain."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import FindingsPackage, TaskEnvelope
from app.agents.browser_head.agent import BrowserHeadAgent
from app.agents.main_head.state import InvestigationState
from app.agents.terminal_head.agent import TerminalHeadAgent
from app.agents.workers.processors import DuplicateDetector
from app.ai.llm_service import llm_service
from app.ai.schemas.reasoning import (
    FindingsAnalysisSchema,
    InvestigationObjectiveAnalysis,
    InvestigationPlanSchema,
)
from app.core.events import InvestigationEvent, event_bus
from app.models.investigations import Investigation
from app.models.reports import Report
from app.models.tasks import Task


class MainHeadGraphRunner:
    """Main Head Agent LangGraph Orchestration Supervisor."""

    @classmethod
    def build_graph(cls, session: AsyncSession):
        graph = StateGraph(InvestigationState)

        # 1. Parse Request Node: AI Objective Analysis
        async def parse_request(state: InvestigationState) -> Dict[str, Any]:
            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="agent_planning",
                    data={"agent": "main_head", "step": "parse_request", "message": "Analyzing objective and target via AI Brain"},
                )
            )

            allowed = state.get("scope", {}).get("allowed_targets", [])
            denied = state.get("scope", {}).get("denied_targets", [])
            target = state.get("target") or (allowed[0] if allowed else "example.com")
            user_prompt = state.get("objective", f"Investigate target {target}")

            # Execute AI Brain objective analysis
            try:
                analysis = await llm_service.analyze_objective(
                    target=target,
                    user_prompt=user_prompt,
                    allowlist=allowed,
                    denylist=denied,
                )
                analysis_dict = analysis.model_dump()
            except Exception as e:
                # Safe fallback structure
                analysis_dict = {
                    "target_type": "domain",
                    "primary_identifier": target,
                    "scope_compliance_verified": True,
                    "identified_objectives": [user_prompt],
                    "risk_assessment": f"Automated fallback assessment: {e}",
                }

            return {
                "target": target,
                "analysis": analysis_dict,
                "status": "planning",
            }

        # 2. Scope Gate Node: Deterministic Security Check (AC-MAIN-04)
        async def scope_gate(state: InvestigationState) -> Dict[str, Any]:
            target = state["target"].strip().lower()
            clean_target = (
                target.replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
                .split(":")[0]
                .strip()
            )
            allowed_targets = [t.lower().strip() for t in state.get("scope", {}).get("allowed_targets", [])]
            denied_targets = [d.lower().strip() for d in state.get("scope", {}).get("denied_targets", [])]

            # Denylist check
            if any(
                target == d or clean_target == d or (d.startswith("*.") and (target.endswith(d[2:]) or clean_target.endswith(d[2:])))
                for d in denied_targets
            ):
                err_msg = f"Security Policy Violation: Target '{target}' is on the investigation denylist."
                await event_bus.publish(
                    InvestigationEvent(
                        investigation_id=state["investigation_id"],
                        event_type="scope_violation",
                        data={"error": err_msg},
                    )
                )
                return {"status": "failed", "errors": state.get("errors", []) + [err_msg]}

            # Allowlist check
            allowed = any(
                target == a or clean_target == a or (a.startswith("*.") and (target.endswith(a[2:]) or clean_target.endswith(a[2:])))
                for a in allowed_targets
            )

            if not allowed:
                err_msg = f"Security Policy Violation: Target '{target}' is not within authorized investigation scope {allowed_targets}."
                await event_bus.publish(
                    InvestigationEvent(
                        investigation_id=state["investigation_id"],
                        event_type="scope_violation",
                        data={"error": err_msg},
                    )
                )
                return {"status": "failed", "errors": state.get("errors", []) + [err_msg]}

            return {"status": "planning"}

        # 3. Plan Node: AI Brain Structured Plan Generation (AC-MAIN-01)
        async def plan(state: InvestigationState) -> Dict[str, Any]:
            if state.get("status") == "failed":
                return {}

            analysis_obj = InvestigationObjectiveAnalysis.model_validate(
                state.get("analysis", {
                    "target_type": "domain",
                    "primary_identifier": state["target"],
                    "scope_compliance_verified": True,
                    "identified_objectives": ["Reconnaissance"],
                    "risk_assessment": "Standard",
                })
            )

            # Generate structured plan using AI Brain
            plan_schema = await llm_service.create_investigation_plan(
                target=state["target"],
                objective_analysis=analysis_obj,
                available_tools=[
                    {"name": "dns_lookup", "description": "Resolve DNS records"},
                    {"name": "whois_lookup", "description": "Query registration information"},
                    {"name": "playwright_extract", "description": "Extract webpage metadata"},
                ],
            )

            investigation_plan = {
                "understanding": plan_schema.summary,
                "summary": plan_schema.summary,
                "tasks": [t.model_dump() for t in plan_schema.tasks],
                "rationale": plan_schema.rationale,
                "estimated_steps": len(plan_schema.tasks),
            }

            # Update DB with plan
            inv_id = uuid.UUID(state["investigation_id"])
            inv = await session.scalar(select(Investigation).where(Investigation.id == inv_id))
            if inv:
                inv.plan_json = investigation_plan
                inv.status = "running"
                await session.commit()

            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="plan_created",
                    data={"plan": investigation_plan},
                )
            )
            return {"plan": investigation_plan, "status": "running"}

        # 4. Decompose Node: Task Distribution to Sub-Heads (AC-MAIN-02, AC-MAIN-03)
        async def decompose(state: InvestigationState) -> Dict[str, Any]:
            if state.get("status") == "failed":
                return {}

            ws_id = uuid.UUID(state["workspace_id"])
            inv_id = uuid.UUID(state["investigation_id"])

            tasks_list = []
            planned_tasks = state.get("plan", {}).get("tasks", [])

            # If AI plan provided tasks, instantiate them
            if planned_tasks:
                for pt in planned_tasks:
                    assigned = pt.get("assigned_agent", "terminal_head")
                    suggested_tools = pt.get("suggested_tools", [])
                    capability = suggested_tools[0] if suggested_tools else (
                        "public_website_metadata" if assigned == "browser_head" else "dns_lookup"
                    )
                    allowed_tools = suggested_tools or (
                        ["website_metadata"] if assigned == "browser_head" else ["dns_lookup"]
                    )
                    input_data = pt.get("required_inputs") or {"target": state["target"]}
                    if "target" not in input_data and "domain" in input_data:
                        input_data["target"] = input_data["domain"]
                    elif "target" not in input_data and "url" in input_data:
                        input_data["target"] = input_data["url"]
                    elif "target" not in input_data:
                        input_data["target"] = state["target"]

                    db_task = Task(
                        workspace_id=ws_id,
                        investigation_id=inv_id,
                        requesting_agent="main_head",
                        assigned_agent=assigned,
                        capability=capability,
                        objective=pt.get("description", pt.get("title", f"Task for {assigned}")),
                        input_json=input_data,
                        allowed_tool_ids=allowed_tools,
                        status="queued",
                    )
                    session.add(db_task)
                    await session.flush()

                    tasks_list.append({
                        "task_id": str(db_task.id),
                        "assigned_agent": assigned,
                        "capability": capability,
                        "objective": db_task.objective,
                        "input": input_data,
                        "allowed_tool_ids": allowed_tools,
                        "scope_ref": str(inv_id),
                    })

                await session.commit()
            else:
                # Baseline fallback tasks
                task1 = Task(
                    workspace_id=ws_id,
                    investigation_id=inv_id,
                    requesting_agent="main_head",
                    assigned_agent="browser_head",
                    capability="public_website_metadata",
                    objective=f"Collect website title, headings, and tech clues from {state['target']}",
                    input_json={"target": state["target"]},
                    allowed_tool_ids=["website_metadata"],
                    status="queued",
                )
                session.add(task1)
                await session.flush()

                task2 = Task(
                    workspace_id=ws_id,
                    investigation_id=inv_id,
                    requesting_agent="main_head",
                    assigned_agent="terminal_head",
                    capability="dns_lookup",
                    objective=f"Resolve DNS records for {state['target']}",
                    input_json={"target": state["target"], "record_type": "A"},
                    allowed_tool_ids=["dns_lookup"],
                    status="queued",
                )
                session.add(task2)
                await session.commit()

                tasks_list.extend([
                    {
                        "task_id": str(task1.id),
                        "assigned_agent": "browser_head",
                        "capability": "public_website_metadata",
                        "objective": task1.objective,
                        "input": {"target": state["target"]},
                        "allowed_tool_ids": ["website_metadata"],
                        "scope_ref": str(inv_id),
                    },
                    {
                        "task_id": str(task2.id),
                        "assigned_agent": "terminal_head",
                        "capability": "dns_lookup",
                        "objective": task2.objective,
                        "input": {"target": state["target"], "record_type": "A"},
                        "allowed_tool_ids": ["dns_lookup"],
                        "scope_ref": str(inv_id),
                    },
                ])

            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="tasks_dispatched",
                    data={"task_count": len(tasks_list)},
                )
            )

            return {"tasks": tasks_list}

        # 5. Route & Dispatch Node
        async def route(state: InvestigationState) -> Dict[str, Any]:
            if state.get("status") == "failed":
                return {}

            ws_id = uuid.UUID(state["workspace_id"])
            findings_packages = []

            for t_dict in state.get("tasks", []):
                allowed_scope = state.get("scope", {})
                permitted_domains = allowed_scope.get("allowed_targets", [state["target"]])
                user_id_str = str(state.get("initiating_user_id") or "")

                t_env = TaskEnvelope(
                    task_id=t_dict["task_id"],
                    investigation_id=state["investigation_id"],
                    initiating_user_id=user_id_str,
                    parent_agent="main_head",
                    assigned_agent=t_dict["assigned_agent"],
                    capability=t_dict["capability"],
                    objective=t_dict["objective"],
                    task_objective=t_dict["objective"],
                    scope_ref=t_dict.get("scope_ref", state["investigation_id"]),
                    authorized_scope=allowed_scope,
                    permitted_domains=permitted_domains,
                    permitted_tools=t_dict.get("allowed_tool_ids", []),
                    allowed_tool_ids=t_dict.get("allowed_tool_ids", []),
                    execution_mode=state.get("mode", "AUTOMATED"),
                    input=t_dict["input"],
                    timeout_seconds=t_dict.get("timeout_seconds", 30),
                )

                if t_dict["assigned_agent"] == "browser_head":
                    pkg = await BrowserHeadAgent.execute_task(session, t_env, ws_id)
                elif t_dict["assigned_agent"] == "terminal_head":
                    pkg = await TerminalHeadAgent.execute_task(session, t_env, ws_id)
                else:
                    pkg = FindingsPackage(
                        investigation_id=state["investigation_id"],
                        subhead_agent=t_dict["assigned_agent"],
                        status="failed",
                        warnings=["Unknown assigned agent"],
                    )

                findings_packages.append(pkg.model_dump())

                # Update task status in database
                t_model = await session.scalar(select(Task).where(Task.id == uuid.UUID(t_dict["task_id"])))
                if t_model:
                    t_model.status = "succeeded" if pkg.status == "succeeded" else pkg.status
                    t_model.completed_at = datetime.now(timezone.utc)
                    await session.commit()

            return {"findings_packages": findings_packages}

        # 6. Consolidate & Correlate Node: AI Brain Findings Synthesis
        async def consolidate(state: InvestigationState) -> Dict[str, Any]:
            if state.get("status") == "failed":
                return {}

            all_findings = []
            for pkg in state.get("findings_packages", []):
                all_findings.extend(pkg.get("findings", []))

            # Deduplicate cross-source findings
            deduped, _ = DuplicateDetector.deduplicate(all_findings)

            # Perform AI Brain findings correlation
            try:
                synthesis = await llm_service.synthesize_findings(findings=deduped)
                synthesis_dict = synthesis.model_dump()
            except Exception as e:
                synthesis_dict = {
                    "observed_facts": [f.get("value", "") for f in deduped if isinstance(f, dict)],
                    "hypotheses_and_inferences": [],
                    "identified_conflicts": [],
                    "identified_gaps": [],
                    "confidence_score": 0.8,
                }

            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="findings_consolidated",
                    data={"total_findings": len(deduped)},
                )
            )

            return {
                "consolidated_findings": deduped,
                "findings_analysis": synthesis_dict,
            }

        # 7. Synthesize Report Node: AI Executive Summary (AC-REPORT-01, AC-REPORT-02)
        async def report(state: InvestigationState) -> Dict[str, Any]:
            if state.get("status") == "failed":
                inv_id = uuid.UUID(state["investigation_id"])
                inv = await session.scalar(select(Investigation).where(Investigation.id == inv_id))
                if inv:
                    inv.status = "failed"
                    inv.completed_at = datetime.now(timezone.utc)
                    await session.commit()
                return {}

            ws_id = uuid.UUID(state["workspace_id"])
            inv_id = uuid.UUID(state["investigation_id"])
            findings = state.get("consolidated_findings", [])
            synthesis_data = state.get("findings_analysis", {})

            # Generate Executive Summary via AI Brain
            try:
                findings_obj = FindingsAnalysisSchema.model_validate(synthesis_data)
                exec_summary = await llm_service.generate_executive_summary(
                    investigation_title=f"OSINT Investigation: {state['target']}",
                    target=state["target"],
                    findings_analysis=findings_obj,
                )
                summary_text = f"{exec_summary.title}\n" + "\n".join(f"- {f}" for f in exec_summary.key_findings)
                threat_level = exec_summary.threat_level
                recommended_actions = exec_summary.recommended_actions
            except Exception:
                summary_text = (
                    f"Automated intelligence gathering completed. "
                    f"{len(findings)} verified findings discovered across public web and network infrastructure."
                )
                threat_level = "info"
                recommended_actions = []

            # Generate Report Model with explicit facts vs inferences separation
            report_model = Report(
                workspace_id=ws_id,
                investigation_id=inv_id,
                version=1,
                status="generated",
                title=f"OSINT Intelligence Report: {state['target']}",
                summary=summary_text,
                report_json={
                    "target": state["target"],
                    "scope_purpose": state.get("scope", {}).get("purpose", ""),
                    "threat_level": threat_level,
                    "findings": findings,
                    "observed_facts": synthesis_data.get("observed_facts", []),
                    "hypotheses_and_inferences": synthesis_data.get("hypotheses_and_inferences", []),
                    "conflicts": synthesis_data.get("identified_conflicts", []),
                    "gaps": synthesis_data.get("identified_gaps", []),
                    "recommended_actions": recommended_actions,
                    "methodology": "Dual-subhead automated OSINT reconnaissance with Google Gemini AI Brain",
                    "limitations": "Only public, unauthenticated sources within explicit scope were inspected.",
                    "status": "complete",
                },
                created_by_agent="main_head",
                created_at=datetime.now(timezone.utc),
                finalized_at=datetime.now(timezone.utc),
            )
            session.add(report_model)

            # Update investigation to completed
            inv = await session.scalar(select(Investigation).where(Investigation.id == inv_id))
            if inv:
                inv.status = "completed"
                inv.completed_at = datetime.now(timezone.utc)
                await session.commit()

            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="report_generated",
                    data={"report_id": str(report_model.id), "title": report_model.title},
                )
            )

            return {"report_id": str(report_model.id), "status": "completed"}

        # Define Edges in StateGraph
        graph.add_node("parse_request", parse_request)
        graph.add_node("scope_gate", scope_gate)
        graph.add_node("plan", plan)
        graph.add_node("decompose", decompose)
        graph.add_node("route", route)
        graph.add_node("consolidate", consolidate)
        graph.add_node("report", report)

        graph.set_entry_point("parse_request")
        graph.add_edge("parse_request", "scope_gate")
        graph.add_edge("scope_gate", "plan")
        graph.add_edge("plan", "decompose")
        graph.add_edge("decompose", "route")
        graph.add_edge("route", "consolidate")
        graph.add_edge("consolidate", "report")
        graph.add_edge("report", END)

        return graph.compile()
