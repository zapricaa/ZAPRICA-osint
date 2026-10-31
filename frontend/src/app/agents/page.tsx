"use client";

import React, { useEffect, useState } from "react";
import { Cpu, Globe, Terminal, Shield, CheckCircle2, AlertTriangle, Activity, Lock } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function AgentCenterPage() {
  const [safeModeStatus, setSafeModeStatus] = useState<any>(null);

  useEffect(() => {
    async function loadStatus() {
      try {
        const res = await apiFetch<any>("/admin/safe-mode/status");
        setSafeModeStatus(res);
      } catch (err) {
        console.error("Failed to load safe mode status:", err);
      }
    }
    loadStatus();
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-blue-400" />
            MULTI-AGENT SUPERVISION & FLEET STATUS
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Supervised AI hierarchy governed by Google Gemini reasoning & strict security controls
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400">
          <CheckCircle2 className="w-4 h-4" />
          <span>SUPERVISION ACTIVE</span>
        </div>
      </div>

      {/* Agents Hierarchy Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Head */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <Cpu className="w-6 h-6" />
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
              {safeModeStatus?.agents?.main_head || "IDLE"}
            </span>
          </div>

          <div>
            <h2 className="font-mono text-base font-bold text-slate-100">MAIN HEAD AGENT</h2>
            <p className="text-xs text-blue-400 font-mono">Master Strategic Planner & Synthesizer</p>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Responsible for receiving user investigation requests, breaking them into targeted sub-tasks, routing them to specialized sub-heads, consolidating intermediate findings, and synthesizing final intelligence reports.
          </p>

          <div className="pt-3 border-t border-slate-800/80 space-y-1.5 text-xs font-mono text-slate-400">
            <div className="flex justify-between">
              <span className="text-slate-500">Model Engine:</span>
              <span className="text-slate-200">gemini-3.8-flash</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Orchestrator:</span>
              <span className="text-emerald-400">LangGraph StateGraph</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Prompt Defense:</span>
              <span className="text-emerald-400">Enforced &lt;untrusted_data&gt;</span>
            </div>
          </div>
        </div>

        {/* Browser Head */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-lg bg-cyan-600/20 text-cyan-400 border border-cyan-500/30">
              <Globe className="w-6 h-6" />
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
              {safeModeStatus?.agents?.browser_head || "IDLE"}
            </span>
          </div>

          <div>
            <h2 className="font-mono text-base font-bold text-slate-100">BROWSER HEAD AGENT</h2>
            <p className="text-xs text-cyan-400 font-mono">Web Reconnaissance Supervisor</p>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Supervises automated browser workers using Playwright. Inspects web pages, extracts structured metadata, captures screenshots, and strictly respects CIDR/domain allowlists and denylists.
          </p>

          <div className="pt-3 border-t border-slate-800/80 space-y-1.5 text-xs font-mono text-slate-400">
            <div className="flex justify-between">
              <span className="text-slate-500">Model Engine:</span>
              <span className="text-slate-200">gemini-3.5-flash-lite</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Egress Firewall:</span>
              <span className="text-emerald-400">SSRF Filter Active</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Automation:</span>
              <span className="text-slate-200">Playwright Headless</span>
            </div>
          </div>
        </div>

        {/* Terminal Head */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <div className="p-2.5 rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
              <Terminal className="w-6 h-6" />
            </div>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
              safeModeStatus?.terminal_execution_enabled
                ? "bg-emerald-950 border-emerald-500/40 text-emerald-300"
                : "bg-slate-800 border-slate-700 text-slate-400"
            }`}>
              {safeModeStatus?.terminal_execution_enabled ? "ENABLED" : "DISABLED"}
            </span>
          </div>

          <div>
            <h2 className="font-mono text-base font-bold text-slate-100">TERMINAL HEAD AGENT</h2>
            <p className="text-xs text-emerald-400 font-mono">CLI & Tool Gateway Supervisor</p>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Manages command execution for approved TIMS tools inside isolated container sandboxes. Rejects raw host execution, disallows arbitrary shell strings, and checks RBAC authorization per execution.
          </p>

          <div className="pt-3 border-t border-slate-800/80 space-y-1.5 text-xs font-mono text-slate-400">
            <div className="flex justify-between">
              <span className="text-slate-500">Model Engine:</span>
              <span className="text-slate-200">gemini-3.5-flash-lite</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Execution Mode:</span>
              <span className="text-amber-400">Docker Isolated Only</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Host Exec:</span>
              <span className="text-rose-400">BLOCKED (FAIL-CLOSED)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
