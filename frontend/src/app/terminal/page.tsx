"use client";

import React, { useEffect, useState } from "react";
import {
  Terminal,
  Shield,
  Play,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  Box,
  Layers,
  Lock
} from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function TerminalControlCenterPage() {
  const [environments, setEnvironments] = useState<any[]>([]);
  const [sandboxStatus, setSandboxStatus] = useState<any | null>(null);
  const [selectedTool, setSelectedTool] = useState<string>("dns_lookup");
  const [targetInput, setTargetInput] = useState<string>("example.com");
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string>("");

  const [executionResult, setExecutionResult] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [envRes, invRes] = await Promise.allSettled([
        apiFetch<any>("/terminal/environments"),
        apiFetch<any>("/investigations/?limit=20"),
      ]);

      if (envRes.status === "fulfilled") {
        setSandboxStatus(envRes.value?.sandbox_status || null);
        setEnvironments(envRes.value?.environments || []);
      }

      if (invRes.status === "fulfilled") {
        const items = invRes.value?.items || invRes.value || [];
        setInvestigations(items);
        if (items.length > 0 && !selectedInvestigationId) {
          setSelectedInvestigationId(items[0].id);
        }
      }
    } catch (err) {
      console.error("Terminal control center load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvestigationId) {
      setError("Please select an active investigation workspace first.");
      return;
    }

    setActionLoading(true);
    setError(null);
    setExecutionResult(null);

    try {
      const payload = {
        investigation_id: selectedInvestigationId,
        tool_id: selectedTool,
        arguments: {
          target: targetInput.trim(),
        },
        timeout_seconds: 30,
      };

      const res = await apiFetch<any>("/terminal/tasks", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setExecutionResult(res);
    } catch (err: any) {
      setError(err.message || "Terminal task execution failed.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <Terminal className="w-5 h-5 text-emerald-400" />
            TERMINAL HEAD — DEDICATED SANDBOX ENVIRONMENT
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Hardened Docker disposable containers • Non-root execution • Zero host access
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono">
            <Lock className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-slate-400">Host Exec:</span>
            <span className="text-rose-400 font-semibold">BLOCKED</span>
          </div>
          <button
            onClick={loadData}
            title="Refresh state"
            className="p-2 text-slate-400 hover:text-slate-200 bg-slate-900 rounded-lg border border-slate-800 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2 font-mono">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Security Status Banner */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 uppercase text-[10px]">Execution Gate</span>
          <div className="font-semibold text-slate-200">
            {sandboxStatus?.terminal_execution_enabled ? "ENABLED (ADMIN)" : "DISABLED (SAFE MODE DEFAULT)"}
          </div>
          <p className="text-[11px] text-slate-500">Requires explicit operator or admin clearance.</p>
        </div>

        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 uppercase text-[10px]">Isolation Backend</span>
          <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
            <Box className="w-3.5 h-3.5" />
            <span>Docker Sandboxed Container</span>
          </div>
          <p className="text-[11px] text-slate-500">Read-only rootfs, tmpfs workspace, cap-drop=ALL.</p>
        </div>

        <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1">
          <span className="text-slate-500 uppercase text-[10px]">Fail-Closed Invariant</span>
          <div className="font-semibold text-amber-400">ENFORCED</div>
          <p className="text-[11px] text-slate-500">If container engine is offline, host execution is rejected.</p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Task Submission Form */}
        <div className="space-y-4">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Play className="w-4 h-4 text-emerald-400" />
              Dispatch Terminal Task
            </h2>

            <form onSubmit={handleExecute} className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Investigation</label>
                <select
                  value={selectedInvestigationId}
                  onChange={(e) => setSelectedInvestigationId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                >
                  {investigations.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.title} ({inv.target})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Approved CLI Tool</label>
                <select
                  value={selectedTool}
                  onChange={(e) => setSelectedTool(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                >
                  <option value="dns_lookup">dns_lookup (DNS Record Inquiry)</option>
                  <option value="whois_lookup">whois_lookup (Domain Registry Analysis)</option>
                  <option value="metadata_extractor">metadata_extractor (ExifTool Analysis)</option>
                  <option value="subdomain_enum">subdomain_enum (Passive Subdomain Enumeration)</option>
                  <option value="cert_inspector">cert_inspector (OpenSSL Certificate Chain)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Target / Parameter *</label>
                <input
                  type="text"
                  required
                  value={targetInput}
                  onChange={(e) => setTargetInput(e.target.value)}
                  placeholder="e.g. example.com or file.pdf"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                />
              </div>

              <button
                type="submit"
                disabled={actionLoading}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-mono text-xs font-semibold uppercase tracking-wider transition"
              >
                {actionLoading ? "EXECUTING IN SANDBOX..." : "DISPATCH IN CONTAINER"}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column (2 spans): Terminal Output Console */}
        <div className="lg:col-span-2 space-y-4">
          <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span>TERMINAL WORKER CONSOLE</span>
              </div>
              {executionResult && (
                <div className="flex items-center gap-3 text-[11px]">
                  <span className="text-slate-500">EXIT: {executionResult.exit_code}</span>
                  <span className="text-slate-500">{executionResult.duration_ms}ms</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] ${
                    executionResult.status === "SUCCESS"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-rose-950 text-rose-400 border border-rose-800"
                  }`}>
                    {executionResult.status}
                  </span>
                </div>
              )}
            </div>

            {/* Terminal Screen */}
            <div className="bg-black/90 p-4 rounded-lg border border-slate-900 min-h-[300px] max-h-[500px] overflow-y-auto text-xs text-emerald-400 font-mono space-y-2">
              {!executionResult ? (
                <div className="text-slate-600 italic">
                  No terminal output. Select an approved tool and dispatch a task to view execution logs.
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <span className="text-slate-500">[zaprica-worker]$ </span>
                    <span className="text-slate-200">{executionResult.command_name} {targetInput}</span>
                  </div>

                  {executionResult.stdout && (
                    <pre className="text-slate-300 whitespace-pre-wrap leading-relaxed">
                      {executionResult.stdout}
                    </pre>
                  )}

                  {executionResult.stderr && (
                    <div className="p-2 rounded bg-rose-950/40 border border-rose-900/60 text-rose-400">
                      <div className="text-[10px] text-rose-500 font-bold uppercase">STDERR:</div>
                      <pre className="whitespace-pre-wrap">{executionResult.stderr}</pre>
                    </div>
                  )}

                  <div className="pt-2 border-t border-slate-900 text-slate-600 text-[10px]">
                    Process finished with exit code {executionResult.exit_code} in {executionResult.duration_ms}ms
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
