"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Truck, Users, Car, DollarSign } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import KpiCard from "@/components/kpi-card";
import type { DashboardSummary, RevenueEntry } from "@/lib/types";

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [revenue, setRevenue] = useState<RevenueEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
      return;
    }
    if (!user) return;

    Promise.all([
      api.get<DashboardSummary>("/api/analytics/dashboard"),
      api.get<RevenueEntry[]>("/api/analytics/revenue?period=monthly&months_back=6"),
    ])
      .then(([dash, rev]) => {
        setSummary(dash);
        setRevenue(rev);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authLoading, router]);

  if (loading || !summary) {
    return <div className="text-gray-500">Loading dashboard...</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          title="Active Loads"
          value={summary.active_loads}
          icon={<Truck size={20} />}
        />
        <KpiCard
          title="Monthly Revenue"
          value={`$${(summary.monthly_revenue ?? 0).toLocaleString()}`}
          icon={<DollarSign size={20} />}
        />
        <KpiCard
          title="Drivers"
          value={summary.total_drivers}
          icon={<Users size={20} />}
        />
        <KpiCard
          title="Vehicles"
          value={summary.total_vehicles}
          icon={<Car size={20} />}
        />
      </div>

      {summary.overdue_receivables > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
          <p className="text-sm text-red-800 font-medium">
            {summary.overdue_receivables} overdue receivable{summary.overdue_receivables !== 1 ? "s" : ""} totaling ${(summary.overdue_amount ?? 0).toLocaleString()}
          </p>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Revenue (Last 6 Months)
        </h2>
        {revenue.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={revenue}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(v) => `$${v.toLocaleString()}`} />
              <Tooltip formatter={(v) => `$${Number(v).toLocaleString()}`} />
              <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-gray-500">No revenue data yet.</p>
        )}
      </div>
    </div>
  );
}
