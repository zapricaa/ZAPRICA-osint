"use client";

import React, { useEffect, useState } from "react";
import {
  UserCheck,
  Shield,
  KeyRound,
  UserPlus,
  Users,
  Terminal,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Copy,
  Check,
  Trash2,
  Power
} from "lucide-react";
import { apiFetch, ApiError } from "@/lib/api";

export default function AdminConsolePage() {
  const [users, setUsers] = useState<any[]>([]);
  const [invitations, setInvitations] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [loginAttempts, setLoginAttempts] = useState<any[]>([]);
  const [safeModeStatus, setSafeModeStatus] = useState<any>(null);

  const [activeTab, setActiveTab] = useState<"users" | "invites" | "sessions" | "audit" | "safemode">("users");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // New Invite form
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("INVESTIGATOR");
  const [createdInvite, setCreatedInvite] = useState<any | null>(null);

  // Create user directly form
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("INVESTIGATOR");

  const loadAll = async () => {
    try {
      const [uRes, invRes, sessRes, logRes, smRes] = await Promise.allSettled([
        apiFetch<any>("/admin/users/"),
        apiFetch<any>("/admin/invitations/"),
        apiFetch<any>("/admin/sessions/"),
        apiFetch<any>("/admin/login-attempts/"),
        apiFetch<any>("/admin/safe-mode/status"),
      ]);

      if (uRes.status === "fulfilled") {
        const u = uRes.value;
        setUsers(Array.isArray(u) ? u : (u?.items || []));
      }
      if (invRes.status === "fulfilled") {
        const inv = invRes.value;
        setInvitations(Array.isArray(inv) ? inv : (inv?.items || []));
      }
      if (sessRes.status === "fulfilled") {
        const s = sessRes.value;
        setSessions(Array.isArray(s) ? s : (s?.items || []));
      }
      if (logRes.status === "fulfilled") {
        const l = logRes.value;
        setLoginAttempts(Array.isArray(l) ? l : (l?.items || []));
      }
      if (smRes.status === "fulfilled") {
        setSafeModeStatus(smRes.value);
      }
    } catch (err) {
      console.error("Admin load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    try {
      const res = await apiFetch<any>("/admin/invitations/", {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail.trim(),
          role_name: inviteRole,
          expires_in_hours: 48,
        }),
      });
      setCreatedInvite(res);
      setInviteEmail("");
      await loadAll();
    } catch (err: any) {
      setError(err.message || "Failed to create invitation link.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setError(null);
    try {
      await apiFetch("/admin/users/", {
        method: "POST",
        body: JSON.stringify({
          email: newEmail.trim(),
          username: newUsername.trim(),
          password: newPassword,
          role_name: newRole,
        }),
      });
      setShowCreateModal(false);
      setNewEmail("");
      setNewUsername("");
      setNewPassword("");
      await loadAll();
    } catch (err: any) {
      setError(err.message || "Failed to provision user.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateStatus = async (userId: string, newStatus: string) => {
    setActionLoading(true);
    try {
      await apiFetch(`/admin/users/${userId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      await loadAll();
    } catch (err: any) {
      setError(err.message || "Failed to update user status.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleTerminal = async () => {
    if (!safeModeStatus) return;
    const nextState = !safeModeStatus.terminal_execution_enabled;
    const confirmMsg = nextState
      ? "SECURITY ALERT: Enable sandboxed terminal execution? Tools will run within Docker containers."
      : "Disable terminal execution? All agent terminal calls will fail closed.";
    if (!window.confirm(confirmMsg)) return;

    setActionLoading(true);
    try {
      await apiFetch("/admin/safe-mode/terminal-execution", {
        method: "POST",
        body: JSON.stringify({ enabled: nextState }),
      });
      await loadAll();
    } catch (err: any) {
      setError(err.message || "Failed to update terminal execution state.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(text);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100 flex items-center gap-2.5">
            <UserCheck className="w-5 h-5 text-blue-400" />
            ADMINISTRATOR SECURITY CONSOLE
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Invite-only user provisioning, RBAC policy enforcement, and execution controls
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-mono text-xs uppercase tracking-wider font-semibold shadow-lg shadow-blue-600/20 transition"
          >
            <UserPlus className="w-4 h-4" />
            <span>Create User</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("users")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "users"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Users ({users.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("invites")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "invites"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <KeyRound className="w-3.5 h-3.5" />
          <span>Invitations ({invitations.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("sessions")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "sessions"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Active Sessions ({sessions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("audit")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "audit"
              ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span>Login Audit Trail ({loginAttempts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("safemode")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition ${
            activeTab === "safemode"
              ? "bg-amber-600/20 text-amber-400 border border-amber-500/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Safe Mode & Execution</span>
        </button>
      </div>

      {/* Users Tab */}
      {activeTab === "users" && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800">
                <tr>
                  <th className="p-3.5">User</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">MFA</th>
                  <th className="p-3.5">Role</th>
                  <th className="p-3.5">Created</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-900/80">
                    <td className="p-3.5">
                      <div className="font-semibold text-slate-200">{u.username}</div>
                      <div className="text-[11px] text-slate-500">{u.email}</div>
                    </td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        u.status === "ACTIVE"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : u.status === "SUSPENDED"
                          ? "bg-amber-950 text-amber-400 border border-amber-800"
                          : "bg-rose-950 text-rose-400 border border-rose-800"
                      }`}>
                        {u.status}
                      </span>
                    </td>
                    <td className="p-3.5">
                      {u.is_mfa_enabled ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Enabled
                        </span>
                      ) : (
                        <span className="text-slate-500">Disabled</span>
                      )}
                    </td>
                    <td className="p-3.5 text-slate-300">
                      {u.roles?.map((r: any) => r.name).join(", ") || "INVESTIGATOR"}
                    </td>
                    <td className="p-3.5 text-slate-500">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3.5 text-right space-x-1">
                      {u.status === "ACTIVE" && (
                        <button
                          onClick={() => handleUpdateStatus(u.id, "SUSPENDED")}
                          className="px-2 py-1 text-[10px] rounded bg-amber-950/40 text-amber-300 hover:bg-amber-900/60 border border-amber-800"
                        >
                          SUSPEND
                        </button>
                      )}
                      {u.status === "SUSPENDED" && (
                        <button
                          onClick={() => handleUpdateStatus(u.id, "ACTIVE")}
                          className="px-2 py-1 text-[10px] rounded bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/60 border border-emerald-800"
                        >
                          ACTIVATE
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Invitations Tab */}
      {activeTab === "invites" && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
            <h3 className="font-mono text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-blue-400" />
              Issue Single-Use Invitation Link
            </h3>

            <form onSubmit={handleCreateInvite} className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Invitee Email *</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="analyst@agency.local"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Role Assignment</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                >
                  <option value="INVESTIGATOR">INVESTIGATOR</option>
                  <option value="ANALYST">ANALYST</option>
                  <option value="ADMINISTRATOR">ADMINISTRATOR</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={actionLoading}
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-mono text-xs font-semibold uppercase tracking-wider"
              >
                {actionLoading ? "GENERATING..." : "GENERATE INVITATION"}
              </button>
            </form>

            {createdInvite && (
              <div className="mt-4 p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 space-y-2">
                <div className="flex items-center justify-between text-xs font-mono text-emerald-300">
                  <span>Invitation Created for {createdInvite.email}</span>
                  <span>Expires in 48h</span>
                </div>
                <div className="flex items-center justify-between bg-slate-950 p-2 rounded border border-slate-800 text-xs font-mono">
                  <span className="truncate mr-2 text-slate-300">{createdInvite.invitation_url || createdInvite.token}</span>
                  <button
                    onClick={() => handleCopy(createdInvite.invitation_url || createdInvite.token)}
                    className="text-slate-400 hover:text-white"
                  >
                    {copiedToken === (createdInvite.invitation_url || createdInvite.token) ? (
                      <Check className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Email</th>
                  <th className="p-3.5">Role</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Expires</th>
                  <th className="p-3.5 text-right">Token</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {invitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-900/80">
                    <td className="p-3.5 font-semibold text-slate-200">{inv.email}</td>
                    <td className="p-3.5 text-slate-300">{inv.role_name || "INVESTIGATOR"}</td>
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        inv.is_used ? "bg-slate-800 text-slate-500" : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      }`}>
                        {inv.is_used ? "USED" : "PENDING"}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-500">
                      {new Date(inv.expires_at).toLocaleString()}
                    </td>
                    <td className="p-3.5 text-right font-mono text-slate-400 truncate max-w-xs">
                      {inv.token ? `${inv.token.slice(0, 12)}...` : "TOKEN"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Safe Mode Controller Tab */}
      {activeTab === "safemode" && (
        <div className="space-y-6">
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-mono text-base font-bold text-slate-100 flex items-center gap-2">
                  <Terminal className="w-5 h-5 text-amber-400" />
                  SAFE STARTUP MODE & EXECUTION CONTROLS
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-1">
                  Enforces default fail-closed posture across all worker runtimes
                </p>
              </div>

              <span className="px-2.5 py-1 rounded bg-amber-950 border border-amber-800 text-amber-300 font-mono text-xs">
                SAFE MODE: ACTIVE
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                <span className="text-xs font-mono text-slate-500 uppercase">Terminal Execution Gate</span>
                <div className="text-lg font-bold font-mono text-slate-200">
                  {safeModeStatus?.terminal_execution_enabled ? "ENABLED" : "DISABLED (DEFAULT)"}
                </div>
                <p className="text-xs text-slate-400">
                  When disabled, any attempt by agents to invoke CLI/host commands fails immediately with a security exception.
                </p>
                <button
                  onClick={handleToggleTerminal}
                  disabled={actionLoading}
                  className={`mt-2 px-3 py-1.5 rounded font-mono text-xs font-semibold uppercase tracking-wider transition ${
                    safeModeStatus?.terminal_execution_enabled
                      ? "bg-rose-600 hover:bg-rose-500 text-white"
                      : "bg-emerald-600 hover:bg-emerald-500 text-white"
                  }`}
                >
                  {safeModeStatus?.terminal_execution_enabled ? "DISABLE TERMINAL EXECUTION" : "ENABLE TERMINAL EXECUTION"}
                </button>
              </div>

              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
                <span className="text-xs font-mono text-slate-500 uppercase">Database & Agent Lifespan</span>
                <div className="text-lg font-bold font-mono text-emerald-400">
                  READ-ONLY VERIFIED
                </div>
                <p className="text-xs text-slate-400">
                  No automated schema modifications or background investigations occur on startup. Execution requires authenticated operator launch.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create User Direct Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <h2 className="text-base font-bold font-mono text-slate-100 flex items-center gap-2">
              <UserPlus className="w-4 h-4 text-blue-400" />
              DIRECT USER PROVISIONING
            </h2>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Email *</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Username *</label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Initial Password (Min 12 chars) *</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Assigned Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
                >
                  <option value="INVESTIGATOR">INVESTIGATOR</option>
                  <option value="ANALYST">ANALYST</option>
                  <option value="ADMINISTRATOR">ADMINISTRATOR</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-xs font-mono text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-mono text-xs uppercase tracking-wider font-semibold rounded-lg"
                >
                  {actionLoading ? "PROVISIONING..." : "PROVISION USER"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
