"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield,
  Activity,
  Search,
  Cpu,
  Wrench,
  FileText,
  Database,
  Sliders,
  FolderLock,
  UserCheck,
  Power
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: Activity },
  { name: "New Investigation", href: "/investigations/new", icon: Search },
  { name: "Workspaces", href: "/investigations", icon: FolderLock },
  { name: "Agent Center", href: "/agents", icon: Cpu },
  { name: "Tool Manager (TIMS)", href: "/tools", icon: Wrench },
  { name: "Evidence Explorer", href: "/evidence", icon: Database },
  { name: "Reports", href: "/reports", icon: FileText },
  { name: "Admin Console", href: "/admin", icon: UserCheck },
];

export function Sidebar() {
  const pathname = usePathname();

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { credentials: "include" });
    } catch {
      // ignore
    }
    window.location.href = "/login";
  };

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col h-screen fixed left-0 top-0 z-40 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-slate-800 bg-slate-900/50">
        <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg border border-blue-500/30">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-wider text-slate-100 font-mono">
            ZAPRICA
          </span>
          <span className="block text-[10px] text-blue-400 uppercase tracking-widest font-mono">
            OSINT Intelligence
          </span>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/80"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-slate-400"}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Safe Mode Indicator & Logout */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/30 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-amber-400 font-mono">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>SAFE STARTUP ACTIVE</span>
          </div>
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            IDLE
          </span>
        </div>
        <p className="text-[11px] text-slate-500">Terminal disabled by default • Strict isolated sandbox</p>

        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 text-xs font-mono text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 py-1.5 rounded border border-slate-800 hover:border-rose-900/40 transition"
        >
          <Power className="w-3.5 h-3.5" />
          <span>SIGN OUT</span>
        </button>
      </div>
    </aside>
  );
}
