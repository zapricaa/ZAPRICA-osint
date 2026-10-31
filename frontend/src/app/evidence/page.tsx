"use client";

import React, { useEffect, useState } from "react";
import { Database, Search, Hash, ExternalLink, ShieldCheck, FileCode, Copy, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function EvidenceExplorerPage() {
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  useEffect(() => {
    async function loadEvidence() {
      try {
        // Query evidence items from investigations
        const invRes = await apiFetch<any>("/investigations/?limit=20");
        const items = invRes?.items || (Array.isArray(invRes) ? invRes : []);
        
        let allEvidence: any[] = [];
        for (const inv of items) {
          try {
            const evRes = await apiFetch<any>(`/investigations/${inv.id}/evidence`);
            const evList = Array.isArray(evRes) ? evRes : (evRes?.items || []);
            allEvidence = [...allEvidence, ...evList.map((e: any) => ({ ...e, investigation_title: inv.title }))];
          } catch {
            // ignore
          }
        }
        setEvidenceList(allEvidence);
      } catch (err) {
        console.error("Failed to load evidence:", err);
      } finally {
        setLoading(false);
      }
    }
    loadEvidence();
  }, []);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filtered = evidenceList.filter((item) => {
    const q = search.toLowerCase();
    return (
      (item.title || "").toLowerCase().includes(q) ||
      (item.sha256 || "").toLowerCase().includes(q) ||
      (item.source_url || "").toLowerCase().includes(q) ||
      (item.investigation_title || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <Database className="w-5 h-5 text-blue-400" />
            EVIDENCE & PROVENANCE EXPLORER
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Immutable artifact store with cryptographic SHA-256 integrity verification
          </p>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400">
          <ShieldCheck className="w-4 h-4" />
          <span>CHAIN-OF-CUSTODY ACTIVE</span>
        </div>
      </div>

      <div className="relative w-full md:w-96">
        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title, SHA-256, or source..."
          className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 font-mono focus:outline-none focus:border-blue-500"
        />
      </div>

      {loading ? (
        <div className="py-16 text-center text-slate-500 font-mono text-xs">
          Scanning evidence repository...
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-slate-800 rounded-xl">
          <Database className="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs text-slate-400 font-mono">No evidence artifacts found.</p>
          <p className="text-[11px] text-slate-600 mt-1">
            Evidence artifacts will be indexed here as investigations execute.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3 flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {item.media_type || "application/octet-stream"}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {item.size_bytes ? `${item.size_bytes} B` : "DATA"}
                  </span>
                </div>

                <h3 className="font-mono text-sm font-semibold text-slate-200">
                  {item.title || "Evidence Artifact"}
                </h3>

                {item.summary && (
                  <p className="text-xs text-slate-400 line-clamp-3">
                    {item.summary}
                  </p>
                )}
              </div>

              <div className="space-y-2 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-500">
                <div className="flex items-center justify-between bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="truncate mr-2 font-mono text-slate-400">
                    {item.sha256 ? `${item.sha256.slice(0, 16)}...` : "NO_HASH"}
                  </span>
                  {item.sha256 && (
                    <button
                      onClick={() => handleCopyHash(item.sha256)}
                      className="text-slate-400 hover:text-slate-200"
                      title="Copy full SHA-256"
                    >
                      {copiedHash === item.sha256 ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  )}
                </div>

                <div className="truncate">
                  Source: <span className="text-slate-400">{item.source_url || "Direct Agent Collector"}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
