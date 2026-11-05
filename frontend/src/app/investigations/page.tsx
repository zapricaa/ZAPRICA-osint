"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { FolderLock, Search, Plus, ArrowRight, Clock, Target, Shield, CheckCircle2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function InvestigationsPage() {
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  useEffect(() => {
    async function loadInvestigations() {
      try {
        const res = await apiFetch<any>("/investigations/");
        const items = res?.items || (Array.isArray(res) ? res : []);
        setInvestigations(items);
      } catch (err) {
        console.error("Failed to load investigations:", err);
      } finally {
        setLoading(false);
      }
    }
    loadInvestigations();
  }, []);

  const filtered = investigations.filter((inv) => {
    const targetVal =
      inv.target ||
      (inv.scope?.allowed_targets && inv.scope.allowed_targets[0]) ||
      "";
    const matchesSearch =
      (inv.title || "").toLowerCase().includes(search.toLowerCase()) ||
      targetVal.toLowerCase().includes(search.toLowerCase());
    const invStatusUpper = (inv.status || "").toUpperCase();
    const matchesStatus =
      statusFilter === "ALL" || invStatusUpper === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <FolderLock className="w-5 h-5 text-blue-400" />
            INVESTIGATION WORKSPACES
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Browse active and historical intelligence operations
          </p>
        </div>

        <Link
          href="/investigations/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-blue-600/20 transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Investigation</span>
        </Link>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or target..."
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 font-mono focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto">
          {["ALL", "DRAFT", "RUNNING", "COMPLETED", "FAILED"].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${
                statusFilter === status
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Investigations List */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 font-mono text-xs">
          Scanning database for workspaces...
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-slate-800 rounded-xl">
          <FolderLock className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-mono">No investigations found matching query.</p>
          <Link
            href="/investigations/new"
            className="mt-3 inline-block text-xs font-mono text-blue-400 hover:underline"
          >
            Launch a new investigation &rarr;
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((inv) => (
            <Link
              key={inv.id}
              href={`/investigations/${inv.id}`}
              className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-blue-500/40 hover:bg-slate-900/80 transition flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                    (inv.status || "").toUpperCase() === "COMPLETED"
                      ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300"
                      : (inv.status || "").toUpperCase() === "FAILED"
                      ? "bg-rose-950/60 border-rose-500/40 text-rose-300"
                      : (inv.status || "").toUpperCase() === "RUNNING"
                      ? "bg-blue-950/60 border-blue-500/40 text-blue-300 animate-pulse"
                      : "bg-slate-800 border-slate-700 text-slate-300"
                  }`}>
                    {(inv.status || "DRAFT").toUpperCase()}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 uppercase">
                    {inv.investigation_type || inv.target_type || "TARGET"}
                  </span>
                </div>

                <h3 className="font-mono text-sm font-semibold text-slate-200 group-hover:text-blue-400 transition line-clamp-1">
                  {inv.title}
                </h3>

                <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                  <Target className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  <span className="truncate">{inv.target || inv.scope?.allowed_targets?.[0] || "N/A"}</span>
                </div>

                {(inv.objective || inv.description) && (
                  <p className="mt-2 text-xs text-slate-500 line-clamp-2">
                    {inv.objective || inv.description}
                  </p>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono text-slate-500">
                <span>Mode: {inv.mode || "AUTO"}</span>
                <span className="text-blue-400 flex items-center gap-1 group-hover:translate-x-0.5 transition">
                  <span>Enter</span>
                  <ArrowRight className="w-3 h-3" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

