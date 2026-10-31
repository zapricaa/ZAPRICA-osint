"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, Lock, User, KeyRound, AlertCircle, ArrowRight, ShieldCheck, Terminal } from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [showMfaField, setShowMfaField] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Bootstrap mode toggle (for initial setup if needed)
  const [isBootstrap, setIsBootstrap] = useState(false);
  const [bootstrapSecret, setBootstrapSecret] = useState("");
  const [bootstrapUsername, setBootstrapUsername] = useState("admin");
  const [bootstrapEmail, setBootstrapEmail] = useState("admin@zaprica.local");
  const [bootstrapSuccess, setBootstrapSuccess] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch<any>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          identifier,
          password,
          mfa_code: mfaCode || null,
        }),
      });

      if (res.mfa_required) {
        setShowMfaField(true);
        setError("Two-Factor Authentication required. Enter the 6-digit code from your authenticator.");
        setLoading(false);
        return;
      }

      router.push("/dashboard");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || "Authentication failed. Access denied.");
      } else {
        setError("Network error connecting to ZAPRICA Gateway.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleBootstrap = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await apiFetch<any>("/auth/bootstrap", {
        method: "POST",
        body: JSON.stringify({
          email: bootstrapEmail,
          username: bootstrapUsername,
          password: password,
          bootstrap_secret: bootstrapSecret,
        }),
      });
      setBootstrapSuccess(true);
      setError(null);
      setIsBootstrap(false);
      setIdentifier(bootstrapUsername);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || "Bootstrap failed. Invalid secret or already initialized.");
      } else {
        setError("Failed to execute one-time super admin bootstrap.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md">
      {/* Brand Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400 mb-3 shadow-[0_0_20px_rgba(59,130,246,0.3)]">
          <Shield className="w-7 h-7" />
        </div>
        <h1 className="text-2xl font-bold font-mono tracking-widest text-slate-100">
          ZAPRICA
        </h1>
        <p className="text-xs uppercase tracking-widest text-blue-400 font-mono mt-1">
          Secure Intelligence Platform
        </p>
        <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-400 font-mono">
          <Lock className="w-3 h-3 text-emerald-400" />
          <span>INVITE-ONLY ACCESS ENFORCED</span>
        </div>
      </div>

      {/* Main Card */}
      <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-xl p-6 shadow-2xl relative overflow-hidden">
        {/* Accent Glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        {bootstrapSuccess && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>Super Administrator initialized! You can now log in below.</span>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!isBootstrap ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Identifier (Email or Username)
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="operator@zaprica.local"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••••••"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 font-mono"
                />
              </div>
            </div>

            {showMfaField && (
              <div className="pt-2 animate-in fade-in duration-200">
                <label className="block text-xs font-mono text-blue-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5" />
                  TOTP Authenticator Token
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.trim())}
                  placeholder="000000"
                  className="w-full bg-slate-950 border border-blue-500/50 rounded-lg px-4 py-2.5 text-center text-lg tracking-[0.5em] text-blue-300 font-mono placeholder:text-slate-700 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-mono text-xs uppercase tracking-wider py-3 rounded-lg font-semibold flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition active:scale-[0.99]"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>AUTHENTICATE OPERATOR</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          /* Bootstrap initial super admin form */
          <form onSubmit={handleBootstrap} className="space-y-4">
            <div className="p-2.5 rounded bg-amber-950/40 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
              <Terminal className="w-4 h-4 shrink-0" />
              <span>One-Time Initial Super Admin Provisioning</span>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Admin Email
              </label>
              <input
                type="email"
                required
                value={bootstrapEmail}
                onChange={(e) => setBootstrapEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Admin Username
              </label>
              <input
                type="text"
                required
                value={bootstrapUsername}
                onChange={(e) => setBootstrapUsername(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Admin Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 uppercase tracking-wider mb-1">
                Bootstrap Secret Key
              </label>
              <input
                type="password"
                required
                value={bootstrapSecret}
                onChange={(e) => setBootstrapSecret(e.target.value)}
                placeholder="From ZAPRICA_BOOTSTRAP_SECRET"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-mono text-xs uppercase tracking-wider py-2.5 rounded-lg font-semibold"
            >
              {loading ? "INITIALIZING..." : "INITIALIZE SUPER ADMIN"}
            </button>
          </form>
        )}

        {/* Footer Navigation */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <a
            href="/accept-invitation"
            className="hover:text-blue-400 hover:underline transition"
          >
            Have an invitation token?
          </a>

          <button
            type="button"
            onClick={() => setIsBootstrap(!isBootstrap)}
            className="text-[11px] text-slate-500 hover:text-amber-400 transition"
          >
            {isBootstrap ? "Back to Login" : "First Time Setup?"}
          </button>
        </div>
      </div>

      {/* Security Notice */}
      <p className="text-center text-[11px] text-slate-600 font-mono mt-6">
        Protected by Argon2id encryption & fail-closed safe startup. Unauthorized access is strictly logged.
      </p>
    </div>
  );
}

