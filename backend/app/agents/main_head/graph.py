import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.main_head.state import InvestigationState
from app.agents.contracts import TaskEnvelope, FindingsPackage
from app.agents.browser_head.agent import BrowserHeadAgent
from app.agents.terminal_head.agent import TerminalHeadAgent
from app.agents.llm_provider import get_llm_provider
from app.core.events import event_bus, InvestigationEvent
from app.models.investigations import Investigation
from app.models.tasks import Task
from app.models.reports import Report, AuditEvent
from app.agents.workers.processors import DuplicateDetector


class MainHeadGraphRunner:
    """Main Head Agent LangGraph Orchestration Supervisor."""

    @classmethod
    def build_graph(cls, session: AsyncSession):
        graph = StateGraph(InvestigationState)

        # 1. Parse Request Node
        async def parse_request(state: InvestigationState) -> Dict[str, Any]:
            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="agent_planning",
                    data={"agent": "main_head", "step": "parse_request", "message": "Analyzing objective and target"}
                )
            )
            # Ensure target is identified from scope
            allowed = state.get("scope", {}).get("allowed_targets", [])
            target = state.get("target") or (allowed[0] if allowed else "example.com")
            return {"target": target, "status": "planning"}

        # 2. Scope Gate Node (AC-MAIN-04: Deterministic Policy Check)
        async def scope_gate(state: InvestigationState) -> Dict[str, Any]:
            target = state["target"].strip().lower()
            allowed_targets = [t.lower() for t in state.get("scope", {}).get("allowed_targets", [])]

            # Check if target is explicitly allowed or wildcard matches
            allowed = any(
                target == a or (a.startswith("*.") and target.endswith(a[2:]))
                for a in allowed_targets
            )

            if not allowed:
                err_msg = f"Security Policy Violation: Target '{target}' is not within authorized investigation scope {allowed_targets}."
                await event_bus.publish(
                    InvestigationEvent(
                        investigation_id=state["investigation_id"],
                        event_type="scope_violation",
                        data={"error": err_msg}
                    )
                )
                return {"status": "failed", "errors": state.get("errors", []) + [err_msg]}

            return {"status": "planning"}

        # 3. Plan Node
        async def plan(state: InvestigationState) -> Dict[str, Any]:
            if state["status"] == "failed":
                return {}

            investigation_plan = {
                "understanding": f"Perform comprehensive public intelligence gathering on {state['target']}",
                "methodology": "Dual-subhead reconnaissance: Browser DOM/HTTP analysis + Terminal DNS resolution",
                "risk_class": "low",
                "estimated_steps": 2,
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
                    data={"plan": investigation_plan}
                )
            )
            return {"plan": investigation_plan, "status": "running"}

        # 4. Decompose Node (AC-MAIN-01, AC-MAIN-02, AC-MAIN-03)
        async def decompose(state: InvestigationState) -> Dict[str, Any]:
            if state["status"] == "failed":
                return {}

            ws_id = uuid.UUID(state["workspace_id"])
            inv_id = uuid.UUID(state["investigation_id"])

            tasks_list = []

            # Task 1: Browser Task -> Browser Head (AC-MAIN-02)
            task1 = Task(
                workspace_id=ws_id,
                investigation_id=inv_id,
                requesting_agent="main_head",
                assigned_agent="browser_head",
                capability="public_website_metadata",
                objective=f"Collect website title, headings, and tech clues from {state['target']}",
                input_json={"target": state["target"]},
                allowed_tool_ids=["website_metadata"],
                status="queued"
            )
            session.add(task1)
            await session.flush()

            tasks_list.append({
                "task_id": str(task1.id),
                "assigned_agent": "browser_head",
                "capability": "public_website_metadata",
                "objective": task1.objective,
                "input": {"target": state["target"]},
                "allowed_tool_ids": ["website_metadata"],
                "scope_ref": str(inv_id)
            })

            # Task 2: Terminal Task -> Terminal Head (AC-MAIN-03)
            task2 = Task(
                workspace_id=ws_id,
                investigation_id=inv_id,
                requesting_agent="main_head",
                assigned_agent="terminal_head",
                capability="dns_lookup",
                objective=f"Resolve DNS records for {state['target']}",
                input_json={"target": state["target"], "record_type": "A"},
                allowed_tool_ids=["dns_lookup"],
                status="queued"
            )
            session.add(task2)
            await session.commit()

            tasks_list.append({
                "task_id": str(task2.id),
                "assigned_agent": "terminal_head",
                "capability": "dns_lookup",
                "objective": task2.objective,
                "input": {"target": state["target"], "record_type": "A"},
                "allowed_tool_ids": ["dns_lookup"],
                "scope_ref": str(inv_id)
            })

            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="tasks_dispatched",
                    data={"task_count": len(tasks_list)}
                )
            )

            return {"tasks": tasks_list}

        # 5. Route & Dispatch Node
        async def route(state: InvestigationState) -> Dict[str, Any]:
            if state["status"] == "failed":
                return {}

            ws_id = uuid.UUID(state["workspace_id"])
            findings_packages = []

            for t_dict in state.get("tasks", []):
                t_env = TaskEnvelope(
                    task_id=t_dict["task_id"],
                    investigation_id=state["investigation_id"],
                    assigned_agent=t_dict["assigned_agent"],
                    capability=t_dict["capability"],
                    objective=t_dict["objective"],
                    scope_ref=t_dict["scope_ref"],
                    allowed_tool_ids=t_dict["allowed_tool_ids"],
                    input=t_dict["input"]
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
                        warnings=["Unknown assigned agent"]
                    )

                findings_packages.append(pkg.model_dump())

                # Update task status in database
                t_model = await session.scalar(select(Task).where(Task.id == uuid.UUID(t_dict["task_id"])))
                if t_model:
                    t_model.status = "succeeded" if pkg.status == "succeeded" else pkg.status
                    t_model.completed_at = datetime.now(timezone.utc)
                    await session.commit()

            return {"findings_packages": findings_packages}

        # 6. Consolidate & Correlate Node
        async def consolidate(state: InvestigationState) -> Dict[str, Any]:
            if state["status"] == "failed":
                return {}

            all_findings = []
            for pkg in state.get("findings_packages", []):
                all_findings.extend(pkg.get("findings", []))

            # Deduplicate cross-source findings
            deduped, _ = DuplicateDetector.deduplicate(all_findings)

            await event_bus.publish(
                InvestigationEvent(
                    investigation_id=state["investigation_id"],
                    event_type="findings_consolidated",
                    data={"total_findings": len(deduped)}
                )
            )

            return {"consolidated_findings": deduped}

        # 7. Synthesize Report Node (AC-REPORT-01, AC-REPORT-02)
        async def report(state: InvestigationState) -> Dict[str, Any]:
            if state["status"] == "failed":
                # Mark investigation failed
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

            # Generate Report Model
            report_model = Report(
                workspace_id=ws_id,
                investigation_id=inv_id,
                version=1,
                status="generated",
                title=f"OSINT Intelligence Report: {state['target']}",
                summary=f"Automated intelligence gathering completed. {len(findings)} verified findings discovered across public web and network infrastructure.",
                report_json={
                    "target": state["target"],
                    "scope_purpose": state.get("scope", {}).get("purpose", ""),
                    "findings": findings,
                    "methodology": "Dual-subhead automated OSINT reconnaissance",
                    "limitations": "Only public, unauthenticated sources within explicit scope were inspected.",
                    "status": "complete"
                },
                created_by_agent="main_head",
                created_at=datetime.now(timezone.utc),
                finalized_at=datetime.now(timezone.utc)
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
                    data={"report_id": str(report_model.id), "title": report_model.title}
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
