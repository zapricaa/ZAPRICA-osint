"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Target, Play, AlertCircle, ArrowLeft, Sliders, Globe, Lock } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function NewInvestigationPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [target, setTarget] = useState("");
  const [targetType, setTargetType] = useState("DOMAIN");
  const [mode, setMode] = useState("AUTOMATED");
  const [allowlist, setAllowlist] = useState("");
  const [denylist, setDenylist] = useState("*.gov, *.mil, localhost, 127.0.0.1, 10.0.0.0/8, 192.168.0.0/16");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const allowlistArr = allowlist
      ? allowlist.split(",").map((s) => s.trim()).filter(Boolean)
      : [target];
    const denylistArr = denylist
      ? denylist.split(",").map((s) => s.trim()).filter(Boolean)
      : [];

    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        target: target.trim(),
        target_type: targetType,
        mode,
        scope: {
          allowlist: allowlistArr,
          denylist: denylistArr,
        },
      };

      const res = await apiFetch<any>("/investigations/", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.push(`/investigations/${res.id}`);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || "Failed to create investigation.");
      } else {
        setError("Network error connecting to investigation service.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-900 rounded-lg border border-slate-800 transition"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold font-mono text-slate-100 flex items-center gap-2">
            <Target className="w-5 h-5 text-blue-400" />
            INITIATE OSINT INVESTIGATION
          </h1>
          <p className="text-xs text-slate-400 font-mono">
            Define target parameters, operational constraints, and authorization boundaries
          </p>
        </div>
      </div>

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
        {error && (
          <div className="mb-6 p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Title & Target Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Investigation Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Acme Corp Infrastructure Mapping"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Primary Target Identifier *
              </label>
              <input
                type="text"
                required
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="e.g. acme-corp.com or 198.51.100.42"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
          </div>

          {/* Target Type & Mode */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Target Classification
              </label>
              <select
                value={targetType}
                onChange={(e) => setTargetType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
              >
                <option value="DOMAIN">DOMAIN NAME / FQDN</option>
                <option value="IP">IP ADDRESS / CIDR</option>
                <option value="USERNAME">ONLINE ALIAS / USERNAME</option>
                <option value="EMAIL">EMAIL ADDRESS</option>
                <option value="ORGANIZATION">ORGANIZATION / ENTITY</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Autonomous Execution Mode
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-blue-500 font-mono"
              >
                <option value="AUTOMATED">AUTOMATED (AI Decomposes & Routes)</option>
                <option value="INTERACTIVE">INTERACTIVE (Operator Confirms Plan)</option>
              </select>
            </div>
          </div>

          {/* Objective Description */}
          <div>
            <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
              Investigation Objective & Strategic Scope
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detail what intelligence you need: DNS topology, SSL certificate chains, exposed HTTP headers, open source footprints..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 font-sans"
            />
          </div>

          {/* Scope Boundaries */}
          <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-4">
            <div className="flex items-center gap-2 text-xs font-mono text-blue-400 font-semibold">
              <Shield className="w-4 h-4" />
              <span>STRICT SCOPE BOUNDARIES (SSRF & EGRESS FIREWALL)</span>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Scope Allowlist (comma separated hostnames/wildcards permitted for inquiry)
              </label>
              <input
                type="text"
                value={allowlist}
                onChange={(e) => setAllowlist(e.target.value)}
                placeholder="Leave blank to default to primary target domain"
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1">
                Scope Denylist (comma separated forbidden domains/subnets — egress firewall drops unconditionally)
              </label>
              <input
                type="text"
                value={denylist}
                onChange={(e) => setDenylist(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-rose-500"
              />
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-blue-600/20 transition active:scale-[0.99]"
            >
              {loading ? (
                <span>CREATING WORKSPACE...</span>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>INITIALIZE & PROCEED</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

