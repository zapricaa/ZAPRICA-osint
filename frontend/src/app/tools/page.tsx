"use client";

import React, { useEffect, useState } from "react";
import { Wrench, Shield, CheckCircle2, AlertTriangle, Plus, Terminal, RefreshCw, Lock } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function ToolsManagerPage() {
  const [tools, setTools] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRegisterModal, setShowRegisterModal] = useState(false);

  // New tool form
  const [toolName, setToolName] = useState("");
  const [version, setVersion] = useState("1.0.0");
  const [description, setDescription] = useState("");
  const [executionType, setExecutionType] = useState("CONTAINER");
  const [riskLevel, setRiskLevel] = useState("LOW");

  const loadTools = async () => {
    try {
      const res = await apiFetch<any>("/tools/");
      const items = Array.isArray(res) ? res : (res?.items || []);
      setTools(items);
    } catch (err) {
      console.error("Failed to load tools:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTools();
  }, []);

  const handleApprove = async (toolId: string) => {
    setActionLoading(true);
    setError(null);
    try {
      await apiFetch(`/admin/tools/${toolId}/approve`, { method: "POST" });
      await loadTools();
    } catch (err: any) {
      setError(err.message || "Failed to approve tool.");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePublish = async (toolId: string) => {
    setActionLoading(true);
    setError(null);
    try {
      await apiFetch(`/admin/tools/${toolId}/publish`, { method: "POST" });
      await loadTools();
    } catch (err: any) {
      setError(err.message || "Failed to publish tool.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    try {
      await apiFetch("/admin/tools/", {
        method: "POST",
        body: JSON.stringify({
          name: toolName.trim(),
          version: version.trim(),
          description: description.trim(),
          execution_type: executionType,
          risk_level: riskLevel,
          timeout_seconds: 30,
        }),
      });
      setShowRegisterModal(false);
      setToolName("");
      setDescription("");
      await loadTools();
    } catch (err: any) {
      setError(err.message || "Failed to register tool draft.");
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
            <Wrench className="w-5 h-5 text-blue-400" />
            TIMS — TOOL INTEGRATION & MANAGEMENT SYSTEM
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Sandboxed tool lifecycle: Draft &rarr; Sandbox Tested &rarr; Approved &rarr; Published
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowRegisterModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-blue-600/20 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Register Tool Draft</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tools Grid */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 font-mono text-xs">
          Loading TIMS tool catalog...
        </div>
      ) : tools.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-slate-800 rounded-xl">
          <Wrench className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-mono">No tools registered in catalog.</p>
          <button
            onClick={() => setShowRegisterModal(true)}
            className="mt-3 text-xs font-mono text-blue-400 hover:underline"
          >
            Register the first tool draft &rarr;
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tools.map((tool) => (
            <div
              key={tool.id}
              className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                    tool.status === "PUBLISHED"
                      ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                      : tool.status === "APPROVED"
                      ? "bg-blue-950/60 border-blue-500/40 text-blue-300"
                      : tool.status === "SANDBOX_TESTED"
                      ? "bg-purple-950/60 border-purple-500/40 text-purple-300"
                      : "bg-slate-800 border-slate-700 text-slate-400"
                  }`}>
                    {tool.status}
                  </span>

                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                    tool.risk_level === "LOW"
                      ? "bg-emerald-950 text-emerald-400"
                      : tool.risk_level === "MEDIUM"
                      ? "bg-amber-950 text-amber-400"
                      : "bg-rose-950 text-rose-400"
                  }`}>
                    RISK: {tool.risk_level}
                  </span>
                </div>

                <h3 className="font-mono text-sm font-semibold text-slate-200">
                  {tool.name} <span className="text-xs text-slate-500 font-mono">v{tool.version}</span>
                </h3>

                <p className="mt-2 text-xs text-slate-400 line-clamp-3">
                  {tool.description || "No description provided."}
                </p>
              </div>

              <div className="space-y-3 pt-3 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>Exec: {tool.execution_type || "CONTAINER"}</span>
                  <span>Timeout: {tool.timeout_seconds || 30}s</span>
                </div>

                {/* Lifecycle action buttons */}
                <div className="flex items-center gap-2">
                  {tool.status === "SANDBOX_TESTED" && (
                    <button
                      onClick={() => handleApprove(tool.id)}
                      disabled={actionLoading}
                      className="flex-1 py-1 px-2 rounded bg-blue-600 hover:bg-blue-500 text-white font-mono text-[11px] font-semibold transition"
                    >
                      APPROVE
                    </button>
                  )}

                  {tool.status === "APPROVED" && (
                    <button
                      onClick={() => handlePublish(tool.id)}
                      disabled={actionLoading}
                      className="flex-1 py-1 px-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-[11px] font-semibold transition"
                    >
                      PUBLISH TO AGENTS
                    </button>
                  )}

                  {tool.status === "PUBLISHED" && (
                    <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Active for Assigned Agents</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register Tool Modal */}
      {showRegisterModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4">
            <h2 className="text-base font-bold font-mono text-slate-100 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-blue-400" />
              REGISTER NEW OSINT TOOL DRAFT
            </h2>

            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 uppercase mb-1">
                  Tool Identifier *
                </label>
                <input
                  type="text"
                  required
                  value={toolName}
                  onChange={(e) => setToolName(e.target.value)}
                  placeholder="e.g. dns-lookup or ssl-cert-auditor"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-slate-300 uppercase mb-1">
                    Version
                  </label>
                  <input
                    type="text"
                    required
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-300 uppercase mb-1">
                    Risk Level
                  </label>
                  <select
                    value={riskLevel}
                    onChange={(e) => setRiskLevel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 uppercase mb-1">
                  Capability Description
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe OSINT outputs, input arguments, and isolation limits..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-blue-500 font-sans"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-3 py-1.5 text-xs font-mono text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs uppercase tracking-wider font-semibold rounded-lg"
                >
                  {actionLoading ? "REGISTERING..." : "REGISTER DRAFT"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

