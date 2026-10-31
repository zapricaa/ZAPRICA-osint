"use client";

import { Bell, Lock, User, CheckCircle2 } from "lucide-react";

export function Navbar() {
  return (
    <header className="h-16 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-30 ml-64">
      {/* Left: Active Workspace Breadcrumb */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          WORKSPACE: DEFAULT-OPS
        </span>
        <span className="text-slate-600">/</span>
        <span className="text-xs text-slate-400 font-mono">ROLE: INVESTIGATOR</span>
      </div>

      {/* Right: Status Badges and Actions */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-300 font-mono text-[11px]">TIMS REGISTRY READY</span>
        </div>

        <button
          title="Security Notifications"
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-900 rounded-lg transition border border-transparent hover:border-slate-800"
        >
          <Bell className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 text-xs font-bold font-mono">
            OP
          </div>
          <div className="hidden md:block text-left text-xs">
            <p className="font-semibold text-slate-200">Operator Alpha</p>
            <p className="text-[10px] text-slate-400 font-mono">secops@zaprica.local</p>
          </div>
        </div>
      </div>
    </header>
  );
}
