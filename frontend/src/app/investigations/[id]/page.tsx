"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Shield,
  Play,
  Square,
  FileText,
  Clock,
  Target,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Globe,
  Terminal,
  Database,
  ArrowRight,
  RefreshCw,
  Hash,
  Activity,
  Layers
} from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function InvestigationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [investigation, setInvestigation] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"tasks" | "evidence" | "events" | "plan">("tasks");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  const loadData = async () => {
    try {
      const [invRes, tasksRes, evidenceRes] = await Promise.allSettled([
        apiFetch<any>(`/investigations/${id}`),
        apiFetch<any>(`/investigations/${id}/tasks`),
        apiFetch<any>(`/investigations/${id}/evidence`),
      ]);

      if (invRes.status === "fulfilled") {
        setInvestigation(invRes.value);
      }
      if (tasksRes.status === "fulfilled") {
        const t = tasksRes.value;
        setTasks(Array.isArray(t) ? t : (t?.items || []));
      }
      if (evidenceRes.status === "fulfilled") {
        const e = evidenceRes.value;
        setEvidence(Array.isArray(e) ? e : (e?.items || []));
      }
    } catch (err: any) {
      console.error("Error loading investigation workspace:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!id) return;
    loadData();

    // Subscribe to SSE live events stream
    try {
      const es = new EventSource(`/api/investigations/${id}/events`, { withCredentials: true });
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setEvents((prev) => [parsed, ...prev]);

          // Refresh investigation status if any operational event occurs
          const eventType = (parsed.event_type || parsed.type || "").toLowerCase();
          if (
            eventType.includes("status") ||
            eventType.includes("plan") ||
            eventType.includes("task") ||
            eventType.includes("finding") ||
            eventType.includes("report") ||
            eventType.includes("complete") ||
            eventType.includes("fail") ||
            eventType.includes("started")
          ) {
            loadData();
          }
        } catch {
          // ignore parsing error
        }
      };

      es.onerror = () => {
        // SSE disconnected, will auto-reconnect
      };
    } catch {
      // SSE not available
    }

    const interval = setInterval(loadData, 5000);

    return () => {
      clearInterval(interval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [id]);

  const handleStart = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await apiFetch(`/investigations/${id}/start`, { method: "POST" });
      await loadData();
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to start investigation.");
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    setActionLoading(true);
    try {
      await apiFetch(`/investigations/${id}/cancel`, { method: "POST" });
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to cancel investigation.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !investigation) {
    return (
      <div className="py-20 text-center font-mono text-xs text-slate-400">
        Loading investigation workspace...
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="py-20 text-center space-y-3">
        <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
        <p className="font-mono text-sm text-slate-300">Investigation workspace not found.</p>
        <Link href="/investigations" className="text-xs font-mono text-blue-400 hover:underline">
          Return to investigations &rarr;
        </Link>
      </div>
    );
  }

  const statusUpper = (investigation.status || "").toUpperCase();
  const isDraft = statusUpper === "DRAFT";
  const isRunning = statusUpper === "RUNNING" || statusUpper === "PLANNING" || statusUpper === "QUEUED";
  const isCompleted = statusUpper === "COMPLETED";

  const targetDisplay =
    investigation.target ||
    (investigation.scope?.allowed_targets && investigation.scope.allowed_targets[0]) ||
    "N/A";
  const targetTypeDisplay =
    investigation.target_type ||
    investigation.investigation_type ||
    "TARGET";
  const objectiveDisplay = investigation.objective || investigation.description || "";

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Workspace Header */}
      <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${
                isCompleted
                  ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                  : statusUpper === "FAILED"
                  ? "bg-rose-950/60 border-rose-500/40 text-rose-300"
                  : isRunning
                  ? "bg-blue-950/60 border-blue-500/40 text-blue-300 animate-pulse"
                  : "bg-slate-800 border-slate-700 text-slate-300"
              }`}>
                {statusUpper}
              </span>
              <span className="text-xs font-mono text-slate-500">ID: {investigation.id}</span>
            </div>

            <h1 className="text-2xl font-bold font-mono text-slate-100">
              {investigation.title}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-1">
              <span className="flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-blue-400" />
                Target: <strong className="text-slate-200">{targetDisplay}</strong> ({targetTypeDisplay})
              </span>
              <span>•</span>
              <span>Mode: {investigation.mode || "AUTOMATED"}</span>
              <span>•</span>
              <span>Created: {new Date(investigation.created_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {isDraft && (
              <button
                onClick={handleStart}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-blue-600/20 transition active:scale-[0.99]"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{actionLoading ? "STARTING..." : "START INVESTIGATION"}</span>
              </button>
            )}

            {isRunning && (
              <button
                onClick={handleCancel}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold transition"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>CANCEL</span>
              </button>
            )}

            {isCompleted && (
              <Link
                href={`/reports?investigation_id=${investigation.id}`}
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-emerald-600/20 transition"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>VIEW INTELLIGENCE REPORT</span>
              </Link>
            )}

            <button
              onClick={loadData}
              title="Refresh Workspace"
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg border border-slate-700 transition"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {objectiveDisplay && (
          <p className="text-xs text-slate-400 border-t border-slate-800/80 pt-3">
            {objectiveDisplay}
          </p>
        )}
      </div>

      {/* Multi-Agent Orchestration Visualizer */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            LangGraph Multi-Agent Pipeline Execution
          </span>
          <span className="text-[10px] font-mono text-slate-500">Google Gemini AI Brain</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-2 text-center text-xs font-mono">
          <div className={`p-2.5 rounded-lg border ${
            !isDraft
              ? "bg-blue-950/40 border-blue-500/40 text-blue-300"
              : "bg-slate-900 border-slate-800 text-slate-500"
          }`}>
            <div className="text-[10px] text-slate-500 uppercase">Stage 1</div>
            <div className="font-semibold mt-0.5">Objective Analysis</div>
          </div>

          <div className={`p-2.5 rounded-lg border ${
            tasks.length > 0
              ? "bg-blue-950/40 border-blue-500/40 text-blue-300"
              : "bg-slate-900 border-slate-800 text-slate-500"
          }`}>
            <div className="text-[10px] text-slate-500 uppercase">Stage 2</div>
            <div className="font-semibold mt-0.5">Plan Generation</div>
          </div>

          <div className={`p-2.5 rounded-lg border ${
            isRunning || isCompleted
              ? "bg-purple-950/40 border-purple-500/40 text-purple-300"
              : "bg-slate-900 border-slate-800 text-slate-500"
          }`}>
            <div className="text-[10px] text-slate-500 uppercase">Stage 3</div>
            <div className="font-semibold mt-0.5">Browser & Terminal Routing</div>
          </div>

          <div className={`p-2.5 rounded-lg border ${
            evidence.length > 0 || isCompleted
              ? "bg-cyan-950/40 border-cyan-500/40 text-cyan-300"
              : "bg-slate-900 border-slate-800 text-slate-500"
          }`}>
            <div className="text-[10px] text-slate-500 uppercase">Stage 4</div>
            <div className="font-semibold mt-0.5">Findings Consolidation</div>
          </div>

          <div className={`p-2.5 rounded-lg border ${
            isCompleted
              ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-300"
              : "bg-slate-900 border-slate-800 text-slate-500"
          }`}>
            <div className="text-[10px] text-slate-500 uppercase">Stage 5</div>
            <div className="font-semibold mt-0.5">Intelligence Synthesis</div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("tasks")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "tasks"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>Agent Tasks ({tasks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("evidence")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "evidence"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>Correlated Evidence ({evidence.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("events")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "events"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Live Stream ({events.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("plan")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "plan"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span>Scope & Strategy</span>
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === "tasks" && (
        <div className="space-y-3">
          {tasks.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-slate-800 rounded-xl">
              <Cpu className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 font-mono">No tasks queued yet.</p>
              <p className="text-[11px] text-slate-600 mt-1 font-mono">
                When started, the Main Head agent analyzes objectives and decomposes tasks.
              </p>
            </div>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                      task.status === "COMPLETED"
                        ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                        : task.status === "RUNNING"
                        ? "bg-blue-950/60 border-blue-500/40 text-blue-300 animate-pulse"
                        : "bg-slate-800 border-slate-700 text-slate-400"
                    }`}>
                      {task.status}
                    </span>
                    <span className="text-xs font-semibold font-mono text-slate-200">
                      {task.title || `Task #${task.id}`}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400">{task.description}</p>

                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500">
                    <span className="flex items-center gap-1">
                      {task.agent_type === "BROWSER_HEAD" ? (
                        <Globe className="w-3.5 h-3.5 text-cyan-400" />
                      ) : (
                        <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                      )}
                      <span>Agent: {task.agent_type}</span>
                    </span>
                    {task.tool_name && (
                      <>
                        <span>•</span>
                        <span>Tool: {task.tool_name}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "evidence" && (
        <div className="space-y-3">
          {evidence.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-slate-800 rounded-xl">
              <Database className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 font-mono">No evidence artifacts recorded yet.</p>
              <p className="text-[11px] text-slate-600 mt-1 font-mono">
                Artifacts collected by workers will be verified with SHA-256 integrity hashes.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {evidence.map((item) => (
                <div
                  key={item.id}
                  className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-semibold text-slate-200">
                      {item.title || "Evidence Artifact"}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {item.media_type || "text/plain"}
                    </span>
                  </div>

                  {item.summary && (
                    <p className="text-xs text-slate-400 line-clamp-3">{item.summary}</p>
                  )}

                  <div className="pt-2 border-t border-slate-800/80 space-y-1 text-[11px] font-mono text-slate-500">
                    <div className="flex items-center gap-1">
                      <Hash className="w-3 h-3 text-slate-600" />
                      <span className="truncate">SHA-256: {item.sha256 || "N/A"}</span>
                    </div>
                    <div>Source: {item.source_url || "Direct tool inquiry"}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "events" && (
        <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 font-mono text-xs max-h-96 overflow-y-auto space-y-2">
          {events.length === 0 ? (
            <div className="text-slate-600 py-6 text-center">
              Listening to live SSE event feed (/v1/investigations/{id}/events)...
            </div>
          ) : (
            events.map((evt, idx) => (
              <div key={idx} className="p-2 rounded bg-slate-900/60 border border-slate-800/80 flex items-start gap-2">
                <span className="text-blue-400 shrink-0">[{evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : "LIVE"}]</span>
                <span className="text-amber-400 shrink-0 font-semibold">{evt.type || "EVENT"}:</span>
                <span className="text-slate-300 break-all">{typeof evt.data === "object" ? JSON.stringify(evt.data) : evt.data || evt.message}</span>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "plan" && (
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-4">
          <h3 className="font-mono text-sm font-semibold text-slate-200">Scope Parameters</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-emerald-400 font-semibold">Scope Allowlist</span>
              <ul className="list-disc list-inside text-slate-400 space-y-1">
                {(investigation.scope?.allowlist || [investigation.target]).map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-rose-400 font-semibold">Scope Denylist (Firewalled)</span>
              <ul className="list-disc list-inside text-slate-400 space-y-1">
                {(investigation.scope?.denylist || ["*.gov", "*.mil", "localhost"]).map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

