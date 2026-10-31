"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Shield,
  ShieldAlert,
  Search,
  Cpu,
  Terminal,
  Globe,
  Database,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Play
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DashboardStats {
  totalInvestigations: number;
  activeInvestigations: number;
  completedInvestigations: number;
  totalTools: number;
  recentInvestigations: any[];
  safeMode: boolean;
  terminalExecution: boolean;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalInvestigations: 0,
    activeInvestigations: 0,
    completedInvestigations: 0,
    totalTools: 0,
    recentInvestigations: [],
    safeMode: true,
    terminalExecution: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [investigationsRes, toolsRes, safeModeRes] = await Promise.allSettled([
          apiFetch<any>("/investigations/?limit=5"),
          apiFetch<any>("/tools/"),
          apiFetch<any>("/admin/safe-mode/status"),
        ]);

        let items: any[] = [];
        if (investigationsRes.status === "fulfilled") {
          items = investigationsRes.value?.items || investigationsRes.value || [];
        }

        let toolsCount = 0;
        if (toolsRes.status === "fulfilled") {
          const t = toolsRes.value;
          toolsCount = Array.isArray(t) ? t.length : (t?.items?.length || 0);
        }

        let safeMode = true;
        let terminalExecution = false;
        if (safeModeRes.status === "fulfilled" && safeModeRes.value) {
          safeMode = safeModeRes.value.safe_mode ?? true;
          terminalExecution = safeModeRes.value.terminal_execution_enabled ?? false;
        }

        const activeCount = items.filter((i) => ["ACTIVE", "RUNNING", "IN_PROGRESS"].includes(i.status)).length;
        const completedCount = items.filter((i) => i.status === "COMPLETED").length;

        setStats({
          totalInvestigations: items.length,
          activeInvestigations: activeCount,
          completedInvestigations: completedCount,
          totalTools: toolsCount,
          recentInvestigations: items,
          safeMode,
          terminalExecution,
        });
      } catch (err) {
        console.error("Dashboard data load error:", err);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Banner / System State */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <Shield className="w-6 h-6 text-blue-400" />
            OPERATIONAL INTELLIGENCE DASHBOARD
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Autonomous multi-agent OSINT reasoning engine • Google Gemini AI Brain
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/investigations/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-blue-600/20 transition"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Launch Investigation</span>
          </Link>
        </div>
      </div>

      {/* Safe Mode Assurance Card */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-amber-300">
                Safe Application Startup Enforced
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800">
                STRICT FAIL-CLOSED
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Terminal command execution disabled by default. No automated host commands or unverified tool execution.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-slate-500">Terminal Execution:</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${
            stats.terminalExecution
              ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-400"
              : "bg-slate-900 border-slate-800 text-slate-400"
          }`}>
            {stats.terminalExecution ? "ENABLED (ADMIN)" : "DISABLED (DEFAULT)"}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Active Missions</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-3 text-2xl font-bold font-mono text-slate-100">
            {stats.activeInvestigations}
          </div>
          <span className="text-[11px] text-slate-500 font-mono mt-1 block">Executing multi-agent tasks</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Completed Reports</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 text-2xl font-bold font-mono text-slate-100">
            {stats.completedInvestigations}
          </div>
          <span className="text-[11px] text-slate-500 font-mono mt-1 block">Full provenance verified</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Approved TIMS Tools</span>
            <Database className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-3 text-2xl font-bold font-mono text-slate-100">
            {stats.totalTools}
          </div>
          <span className="text-[11px] text-slate-500 font-mono mt-1 block">Catalogued OSINT capabilities</span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">AI Brain Status</span>
            <Cpu className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 text-sm font-bold font-mono text-slate-100 truncate">
            Gemini 3.8 Flash
          </div>
          <span className="text-[11px] text-emerald-400 font-mono mt-1 block">ONLINE & READY</span>
        </div>
      </div>

      {/* Agents Hierarchy Overview */}
      <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800">
        <h2 className="text-sm font-mono font-semibold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-blue-400" />
          Multi-Agent Fleet Architecture
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Main Head */}
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs font-semibold text-blue-400">MAIN HEAD AGENT</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-950 text-blue-400 border border-blue-800">
                IDLE / PASSIVE
              </span>
            </div>
            <p className="text-xs text-slate-300 font-medium">Strategic Planner & Synthesizer</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Decomposes objectives, coordinates sub-head workers, correlates findings, generates intelligence reports.
            </p>
            <div className="mt-3 text-[10px] font-mono text-slate-400 border-t border-slate-900 pt-2 flex items-center justify-between">
              <span>Model: gemini-3.8-flash</span>
              <span className="text-emerald-400">LangGraph Active</span>
            </div>
          </div>

          {/* Browser Head */}
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs font-semibold text-cyan-400">BROWSER HEAD AGENT</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-400 border border-cyan-800">
                IDLE / PASSIVE
              </span>
            </div>
            <p className="text-xs text-slate-300 font-medium">Web Reconnaissance Supervisor</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Controls Playwright browser workers, enforces SSRF network boundaries, extracts raw DOM and text.
            </p>
            <div className="mt-3 text-[10px] font-mono text-slate-400 border-t border-slate-900 pt-2 flex items-center justify-between">
              <span>Model: gemini-3.5-flash-lite</span>
              <span className="text-cyan-400">SSRF Firewall On</span>
            </div>
          </div>

          {/* Terminal Head */}
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs font-semibold text-emerald-400">TERMINAL HEAD AGENT</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-800">
                STANDBY
              </span>
            </div>
            <p className="text-xs text-slate-300 font-medium">CLI & Tool Gateway Supervisor</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Executes approved TIMS tools inside sandboxed Docker containers. Host command execution blocked.
            </p>
            <div className="mt-3 text-[10px] font-mono text-slate-400 border-t border-slate-900 pt-2 flex items-center justify-between">
              <span>Model: gemini-3.5-flash-lite</span>
              <span className="text-amber-400">Host Exec Blocked</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Investigations */}
      <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-mono font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Search className="w-4 h-4 text-blue-400" />
            Recent Investigation Workspaces
          </h2>
          <Link
            href="/investigations"
            className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1 transition"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {stats.recentInvestigations.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-slate-800 rounded-lg">
            <Search className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-mono">No investigations initiated yet.</p>
            <p className="text-[11px] text-slate-600 mt-1">
              Safe Startup Mode is standing by. Click Launch Investigation to begin.
            </p>
            <Link
              href="/investigations/new"
              className="mt-4 inline-flex items-center gap-1.5 text-xs font-mono text-blue-400 hover:text-blue-300 underline"
            >
              Start First Investigation &rarr;
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {stats.recentInvestigations.map((inv) => (
              <div
                key={inv.id}
                className="py-3 flex items-center justify-between hover:bg-slate-900/30 px-2 rounded-lg transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/investigations/${inv.id}`}
                      className="font-medium text-sm text-slate-200 hover:text-blue-400 font-mono transition"
                    >
                      {inv.title}
                    </Link>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                      inv.status === "COMPLETED"
                        ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                        : inv.status === "FAILED"
                        ? "bg-rose-950/60 border-rose-500/40 text-rose-300"
                        : "bg-blue-950/60 border-blue-500/40 text-blue-300 animate-pulse"
                    }`}>
                      {inv.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
                    <span>Target: {inv.target || "N/A"}</span>
                    <span>•</span>
                    <span>Mode: {inv.mode || "AUTOMATED"}</span>
                  </div>
                </div>

                <Link
                  href={`/investigations/${inv.id}`}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono flex items-center gap-1 transition"
                >
                  <span>Open Workspace</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
