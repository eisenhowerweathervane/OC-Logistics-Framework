"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { RevenueEntry, FleetUtilization, FuelCostEntry } from "@/lib/types";

export default function AnalyticsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [revenue, setRevenue] = useState<RevenueEntry[]>([]);
  const [utilization, setUtilization] = useState<FleetUtilization[]>([]);
  const [fuel, setFuel] = useState<FuelCostEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) { router.replace("/login"); return; }
    if (!user) return;

    Promise.all([
      api.get<RevenueEntry[]>("/api/analytics/revenue?period=monthly&months_back=6").catch(() => []),
      api.get<FleetUtilization[]>("/api/analytics/fleet-utilization").catch(() => []),
      api.get<FuelCostEntry[]>("/api/analytics/fuel-costs?months_back=6").catch(() => []),
    ]).then(([r, u, f]) => {
      setRevenue(r);
      setUtilization(u);
      setFuel(f);
    }).finally(() => setLoading(false));
  }, [user, authLoading, router]);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue */}
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Monthly Revenue</h2>
          {revenue.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={revenue}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" fontSize={12} />
                <YAxis fontSize={12} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v) => `$${Number(v).toLocaleString()}`} />
                <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-500">No revenue data.</p>
          )}
        </div>

        {/* Fuel costs */}
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Fuel Costs</h2>
          {fuel.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={fuel}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" fontSize={12} />
                <YAxis fontSize={12} tickFormatter={(v) => `$${v}`} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="total_cost" stroke="#ef4444" name="Total Cost" />
                <Line type="monotone" dataKey="avg_price_per_gallon" stroke="#f59e0b" name="Avg $/gal" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-500">No fuel data.</p>
          )}
        </div>

        {/* Fleet utilization */}
        <div className="bg-white rounded-lg border p-6 lg:col-span-2">
          <h2 className="font-semibold text-gray-900 mb-4">Fleet Utilization</h2>
          {utilization.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Driver</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Loads</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Miles</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {utilization.map((u) => (
                    <tr key={u.driver_id}>
                      <td className="px-4 py-3 text-sm font-medium">{u.driver_name}</td>
                      <td className="px-4 py-3 text-sm text-right">{u.loads_count}</td>
                      <td className="px-4 py-3 text-sm text-right">${u.total_revenue.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm text-right">{u.total_miles.toLocaleString()}</td>
                      <td className="px-4 py-3 text-sm">{u.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">No utilization data.</p>
          )}
        </div>
      </div>
    </div>
  );
}
