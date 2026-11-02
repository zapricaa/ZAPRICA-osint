"use client";

import React, { useEffect, useState } from "react";
import {
  Globe,
  Shield,
  Play,
  Square,
  Lock,
  Unlock,
  Camera,
  Download,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Layers,
  ArrowRight
} from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function BrowserControlCenterPage() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any | null>(null);
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string>("");
  const [profileName, setProfileName] = useState<string>("default");

  const [targetUrl, setTargetUrl] = useState<string>("https://example.com");
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Manual import form for HUMAN_ASSISTED_ONLY (e.g. Epieos)
  const [showImportForm, setShowImportForm] = useState<boolean>(false);
  const [importTitle, setImportTitle] = useState<string>("");
  const [importSummary, setImportSummary] = useState<string>("");
  const [importRawData, setImportRawData] = useState<string>("");

  const loadData = async () => {
    try {
      const [sessRes, invRes] = await Promise.allSettled([
        apiFetch<any>("/browser/sessions"),
        apiFetch<any>("/investigations/?limit=20"),
      ]);

      if (sessRes.status === "fulfilled") {
        const s = sessRes.value || [];
        setSessions(s);
        if (s.length > 0 && !activeSession) {
          setActiveSession(s[0]);
        }
      }

      if (invRes.status === "fulfilled") {
        const invs = invRes.value?.items || invRes.value || [];
        setInvestigations(invs);
        if (invs.length > 0 && !selectedInvestigationId) {
          setSelectedInvestigationId(invs[0].id);
        }
      }
    } catch (err) {
      console.error("Browser control center load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStartSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvestigationId) {
      setError("Please select an investigation workspace first.");
      return;
    }
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await apiFetch<any>("/browser/sessions", {
        method: "POST",
        body: JSON.stringify({
          investigation_id: selectedInvestigationId,
          profile_name: profileName.trim() || "default",
          headless: false, // Visible headed browser for local human interaction
        }),
      });
      setActiveSession(res);
      setSuccessMsg("Dedicated browser instance launched successfully!");
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to launch browser session.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleNavigate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSession) return;
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await apiFetch<any>(`/browser/sessions/${activeSession.session_id}/navigate`, {
        method: "POST",
        body: JSON.stringify({ target_url: targetUrl }),
      });
      setSuccessMsg(`Navigated to ${res.current_url}. Policy: ${res.policy_type}`);
      if (res.policy_type === "HUMAN_ASSISTED_ONLY") {
        setShowImportForm(true);
      }
      await loadData();
    } catch (err: any) {
      setError(err.message || "Navigation failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmAuth = async () => {
    if (!activeSession) return;
    setActionLoading(true);
    setError(null);
    try {
      const res = await apiFetch<any>(`/browser/sessions/${activeSession.session_id}/confirm-authentication`, {
        method: "POST",
      });
      setActiveSession(res);
      setSuccessMsg("User authentication confirmed! Session status set to USER_AUTHENTICATED.");
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to confirm authentication.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCaptureScreenshot = async () => {
    if (!activeSession) return;
    setActionLoading(true);
    setError(null);
    try {
      const res = await apiFetch<any>(`/browser/sessions/${activeSession.session_id}/screenshot`, {
        method: "POST",
      });
      setSuccessMsg(`Screenshot captured and preserved! SHA-256: ${res.sha256}`);
    } catch (err: any) {
      setError(err.message || "Failed to capture screenshot.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleImportManualData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeSession) return;
    setActionLoading(true);
    setError(null);
    try {
      const res = await apiFetch<any>(`/browser/sessions/${activeSession.session_id}/import-manual-result`, {
        method: "POST",
        body: JSON.stringify({
          title: importTitle,
          summary: importSummary,
          raw_data: importRawData,
          source_url: activeSession.current_url || targetUrl,
        }),
      });
      setSuccessMsg(`Manual result verified and saved as finding! Artifact SHA-256: ${res.sha256}`);
      setImportTitle("");
      setImportSummary("");
      setImportRawData("");
      setShowImportForm(false);
    } catch (err: any) {
      setError(err.message || "Failed to import manual result.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopSession = async () => {
    if (!activeSession) return;
    setActionLoading(true);
    try {
      await apiFetch(`/browser/sessions/${activeSession.session_id}/stop`, { method: "POST" });
      setActiveSession(null);
      setSuccessMsg("Browser session closed cleanly.");
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to close browser.");
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
            <Globe className="w-5 h-5 text-cyan-400" />
            BROWSER HEAD — DEDICATED BROWSER ENVIRONMENT
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Isolated Playwright persistent context • Human login system • Epieos & policy gate
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeSession && (
            <button
              onClick={handleStopSession}
              disabled={actionLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs font-mono hover:bg-rose-900/60 transition"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Stop Browser</span>
            </button>
          )}
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

      {successMsg && (
        <div className="p-3.5 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2 font-mono">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Launch or Select Session */}
        <div className="space-y-4">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Play className="w-4 h-4 text-cyan-400" />
              Launch Dedicated Browser
            </h2>

            <form onSubmit={handleStartSession} className="space-y-3">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Investigation</label>
                <select
                  value={selectedInvestigationId}
                  onChange={(e) => setSelectedInvestigationId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                >
                  {investigations.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      {inv.title} ({inv.target})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Isolated Profile Name</label>
                <input
                  type="text"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  placeholder="e.g. default or osint_session"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                />
              </div>

              <button
                type="submit"
                disabled={actionLoading}
                className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-mono text-xs font-semibold uppercase tracking-wider transition"
              >
                {actionLoading ? "STARTING..." : "START PERSISTENT BROWSER"}
              </button>
            </form>
          </div>

          {/* Active Sessions List */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
              Active Browser Sessions ({sessions.length})
            </h3>
            {sessions.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono italic">No active browser instances running.</p>
            ) : (
              <div className="space-y-2">
                {sessions.map((s) => (
                  <button
                    key={s.session_id}
                    onClick={() => setActiveSession(s)}
                    className={`w-full p-2.5 rounded-lg border text-left text-xs font-mono transition ${
                      activeSession?.session_id === s.session_id
                        ? "bg-cyan-950/40 border-cyan-500/40 text-cyan-300"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-slate-200">{s.profile_id?.slice(0, 8)}...</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                        {s.status}
                      </span>
                    </div>
                    <div className="truncate text-slate-500">{s.current_url || "Empty Page"}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (2 spans): Browser Controls, Navigation, and Human Auth */}
        <div className="lg:col-span-2 space-y-4">
          {!activeSession ? (
            <div className="py-24 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
              <Globe className="w-10 h-10 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400 font-mono">No active browser context selected.</p>
              <p className="text-[11px] text-slate-600 mt-1">
                Launch a persistent browser session on the left to start dedicated web intelligence.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Session Status Bar */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">STATUS:</span>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                      activeSession.status === "USER_AUTHENTICATED"
                        ? "bg-emerald-950 border-emerald-500 text-emerald-300"
                        : activeSession.status === "LOGIN_REQUIRED"
                        ? "bg-amber-950 border-amber-500 text-amber-300 animate-pulse"
                        : "bg-slate-800 border-slate-700 text-slate-300"
                    }`}>
                      {activeSession.status}
                    </span>
                  </div>

                  <span className="text-slate-600">|</span>

                  <div className="text-slate-400">
                    TABS: <strong>{activeSession.active_tab_count || 1}</strong>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCaptureScreenshot}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 text-xs font-mono transition"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    <span>Capture Proof</span>
                  </button>
                </div>
              </div>

              {/* Human Login Prompt Banner */}
              {activeSession.status === "LOGIN_REQUIRED" && (
                <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 space-y-3 font-mono text-xs">
                  <div className="flex items-center gap-2 font-semibold text-amber-300">
                    <Lock className="w-4 h-4 text-amber-400" />
                    <span>OPERATOR ACTION REQUIRED: MANUAL LOGIN & 2FA</span>
                  </div>
                  <p className="text-[11px] leading-relaxed text-amber-200/80">
                    Please switch to the dedicated browser window, complete your login challenge, enter credentials manually, and solve any MFA/CAPTCHA. Once logged in, click the confirmation button below.
                  </p>
                  <button
                    onClick={handleConfirmAuth}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded text-xs uppercase tracking-wider transition"
                  >
                    <Unlock className="w-3.5 h-3.5" />
                    <span>CONFIRM USER AUTHENTICATED</span>
                  </button>
                </div>
              )}

              {/* Navigation URL Bar */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <form onSubmit={handleNavigate} className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <Globe className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                    <input
                      type="url"
                      required
                      value={targetUrl}
                      onChange={(e) => setTargetUrl(e.target.value)}
                      placeholder="https://example.com or https://epieos.com"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-mono text-xs font-semibold uppercase tracking-wider transition"
                  >
                    {actionLoading ? "NAVIGATING..." : "NAVIGATE"}
                  </button>
                </form>

                {activeSession.current_url && (
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
                    <span className="truncate">Active Page: {activeSession.current_url}</span>
                    <span className="text-cyan-400 shrink-0">SSRF Enforced</span>
                  </div>
                )}
              </div>

              {/* Special Epieos / Human-Assisted Result Import Form */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Download className="w-4 h-4 text-cyan-400" />
                    Manual Result Import (Epieos & Human-Assisted Sites)
                  </h3>
                  <button
                    onClick={() => setShowImportForm(!showImportForm)}
                    className="text-xs font-mono text-cyan-400 hover:underline"
                  >
                    {showImportForm ? "Hide Form" : "Import Findings"}
                  </button>
                </div>

                {showImportForm && (
                  <form onSubmit={handleImportManualData} className="space-y-3 pt-2">
                    <p className="text-[11px] text-slate-400 font-mono leading-relaxed">
                      For sites under the HUMAN_ASSISTED_ONLY policy (such as Epieos), the agent never automates clicks or queries. Manually execute your search in the browser, and import the verified findings below.
                    </p>

                    <div>
                      <label className="block text-xs font-mono text-slate-400 mb-1">Finding Title *</label>
                      <input
                        type="text"
                        required
                        value={importTitle}
                        onChange={(e) => setImportTitle(e.target.value)}
                        placeholder="e.g. Epieos Profile: Associated Google & Twitter Account"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-slate-400 mb-1">Executive Summary</label>
                      <input
                        type="text"
                        value={importSummary}
                        onChange={(e) => setImportSummary(e.target.value)}
                        placeholder="Brief synopsis of observed intelligence"
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-slate-400 mb-1">Raw Output / Extracted Data *</label>
                      <textarea
                        rows={3}
                        required
                        value={importRawData}
                        onChange={(e) => setImportRawData(e.target.value)}
                        placeholder="Paste JSON or text report..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-mono text-xs font-semibold uppercase tracking-wider transition"
                    >
                      {actionLoading ? "SAVING..." : "SAVE VERIFIED FINDING"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
