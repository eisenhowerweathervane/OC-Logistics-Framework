"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Truck,
  Users,
  Car,
  ShieldCheck,
  BarChart3,
  Target,
  DollarSign,
  LogOut,
  FlaskConical,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { SandboxStatus } from "@/lib/types";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/loads", label: "Loads", icon: Truck },
  { href: "/fleet/drivers", label: "Drivers", icon: Users },
  { href: "/fleet/vehicles", label: "Vehicles", icon: Car },
  { href: "/compliance", label: "Compliance", icon: ShieldCheck },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/scoring", label: "Scoring", icon: Target },
  { href: "/receivables", label: "Receivables", icon: DollarSign },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [sandboxMode, setSandboxMode] = useState(false);
  const [toggling, setToggling] = useState(false);

  const checkSandbox = useCallback(async () => {
    try {
      const status = await api.get<SandboxStatus>("/api/sandbox/status");
      setSandboxMode(status.sandbox_mode);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (user) checkSandbox();
  }, [user, checkSandbox]);

  const handleToggleSandbox = async () => {
    const action = sandboxMode ? "deactivate" : "activate";
    const msg = sandboxMode
      ? "Switch back to production? Sandbox data will be removed."
      : "Switch to sandbox mode? This creates a demo environment with sample data.";

    if (!confirm(msg)) return;

    setToggling(true);
    try {
      const result = await api.post<SandboxStatus>("/api/sandbox/toggle");
      setSandboxMode(result.sandbox_mode);
      // Reload the page to refresh all data from the new DB
      window.location.reload();
    } catch {
      alert(`Failed to ${action} sandbox mode`);
    } finally {
      setToggling(false);
    }
  };

  if (!user) return null;

  return (
    <aside
      className={clsx(
        "w-64 flex flex-col min-h-screen transition-colors",
        sandboxMode
          ? "bg-amber-900 text-white"
          : "bg-gray-900 text-white"
      )}
    >
      <div className={clsx(
        "p-4 border-b",
        sandboxMode ? "border-amber-700" : "border-gray-700"
      )}>
        <h1 className="text-lg font-bold">OC Logistics</h1>
        <p className="text-xs text-gray-400 mt-1">{user.email}</p>
        {sandboxMode && (
          <div className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-amber-300">
            <FlaskConical size={14} />
            SANDBOX MODE
          </div>
        )}
      </div>

      <nav className="flex-1 py-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                active
                  ? sandboxMode
                    ? "bg-amber-700 text-white"
                    : "bg-blue-600 text-white"
                  : sandboxMode
                    ? "text-amber-200 hover:bg-amber-800 hover:text-white"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white",
              )}
            >
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className={clsx(
        "p-4 border-t space-y-3",
        sandboxMode ? "border-amber-700" : "border-gray-700"
      )}>
        <button
          onClick={handleToggleSandbox}
          disabled={toggling}
          className={clsx(
            "flex items-center gap-2 text-sm w-full transition-colors",
            toggling && "opacity-50 cursor-wait",
            sandboxMode
              ? "text-amber-300 hover:text-white"
              : "text-gray-400 hover:text-white"
          )}
        >
          <FlaskConical size={16} />
          {toggling
            ? "Switching..."
            : sandboxMode
              ? "Exit Sandbox"
              : "Sandbox Mode"}
        </button>

        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
