"use client";

import React, { useEffect, useState } from "react";
import { FileText, Download, ShieldCheck, AlertCircle, ArrowRight, Printer, Sparkles } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function ReportsPage() {
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadReports() {
      try {
        const res = await apiFetch<any>("/investigations/?limit=20");
        const items = res?.items || (Array.isArray(res) ? res : []);
        setInvestigations(items);

        // If URL has ?investigation_id=, fetch that report
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          const invId = params.get("investigation_id");
          if (invId) {
            try {
              const rep = await apiFetch<any>(`/investigations/${invId}/report`);
              setSelectedReport(rep);
            } catch {
              // ignore
            }
          }
        }
      } catch (err) {
        console.error("Failed to load reports:", err);
      } finally {
        setLoading(false);
      }
    }
    loadReports();
  }, []);

  const handleSelectInvestigation = async (invId: string) => {
    try {
      const rep = await apiFetch<any>(`/investigations/${invId}/report`);
      setSelectedReport(rep);
    } catch {
      setSelectedReport(null);
    }
  };

  const handleExportJson = () => {
    if (!selectedReport) return;
    const blob = new Blob([JSON.stringify(selectedReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ZAPRICA_Report_${selectedReport.id || "export"}.json`;
    a.click();
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-blue-400" />
            INTELLIGENCE REPORTS & SYNTHESIS
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Empirical evidence separated from analytical inferences • Provenance backed
          </p>
        </div>

        {selectedReport && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportJson}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs font-mono transition"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-semibold transition"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print / PDF</span>
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Investigation Selector */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
            Select Investigation
          </h2>
          <div className="space-y-1.5 max-h-[70vh] overflow-y-auto">
            {investigations.map((inv) => (
              <button
                key={inv.id}
                onClick={() => handleSelectInvestigation(inv.id)}
                className={`w-full text-left p-3 rounded-xl border transition ${
                  selectedReport?.investigation_id === inv.id
                    ? "bg-blue-600/20 border-blue-500/40 text-blue-300"
                    : "bg-slate-900/50 border-slate-800 text-slate-300 hover:bg-slate-900/80"
                }`}
              >
                <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                  <span className="text-slate-500">{inv.target}</span>
                  <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                    {inv.status}
                  </span>
                </div>
                <div className="font-mono text-xs font-semibold truncate">
                  {inv.title}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right Column: Report Viewer */}
        <div className="lg:col-span-3">
          {!selectedReport ? (
            <div className="py-24 text-center border border-dashed border-slate-800 rounded-xl">
              <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 font-mono">
                Select an investigation from the left to view or generate its intelligence report.
              </p>
            </div>
          ) : (
            <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-6">
              {/* Report Header */}
              <div className="border-b border-slate-800 pb-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-blue-400">INTELLIGENCE REPORT</span>
                  <span className="text-xs font-mono text-slate-500">
                    Confidence: <strong>{selectedReport.confidence_score ? `${(selectedReport.confidence_score * 100).toFixed(0)}%` : "HIGH"}</strong>
                  </span>
                </div>
                <h2 className="text-xl font-bold font-mono text-slate-100">
                  {selectedReport.title || "Executive Intelligence Assessment"}
                </h2>
              </div>

              {/* Executive Summary */}
              {selectedReport.executive_summary && (
                <div className="space-y-2">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    Executive Summary
                  </h3>
                  <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 leading-relaxed font-sans">
                    {selectedReport.executive_summary}
                  </div>
                </div>
              )}

              {/* Observed Facts vs Analytical Inferences Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Observed Facts */}
                <div className="space-y-2">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Empirical Observed Facts
                  </h3>
                  <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-xs text-slate-300 space-y-2 font-sans min-h-[140px]">
                    {selectedReport.observed_facts ? (
                      Array.isArray(selectedReport.observed_facts) ? (
                        <ul className="list-disc list-inside space-y-1">
                          {selectedReport.observed_facts.map((fact: string, idx: number) => (
                            <li key={idx}>{fact}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>{selectedReport.observed_facts}</p>
                      )
                    ) : (
                      <p className="text-slate-500 italic">No empirical facts recorded.</p>
                    )}
                  </div>
                </div>

                {/* Analytical Inferences */}
                <div className="space-y-2">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    Analytical Inferences (AI Hypotheses)
                  </h3>
                  <div className="p-4 rounded-lg bg-purple-950/20 border border-purple-500/30 text-xs text-slate-300 space-y-2 font-sans min-h-[140px]">
                    {selectedReport.analytical_inferences ? (
                      Array.isArray(selectedReport.analytical_inferences) ? (
                        <ul className="list-disc list-inside space-y-1">
                          {selectedReport.analytical_inferences.map((inf: string, idx: number) => (
                            <li key={idx}>{inf}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>{selectedReport.analytical_inferences}</p>
                      )
                    ) : (
                      <p className="text-slate-500 italic">No analytical inferences noted.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Data Inconsistencies / Conflicts */}
              {selectedReport.inconsistencies && (
                <div className="space-y-2">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Identified Inconsistencies & Source Conflicts
                  </h3>
                  <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/30 text-xs text-amber-200">
                    {selectedReport.inconsistencies}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
