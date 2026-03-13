"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ComplianceAlert } from "@/lib/types";

interface IftaReturn {
  id: string;
  year: number;
  quarter: number;
  status: string;
  total_miles: number;
  total_gallons: number;
}

export default function CompliancePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [alerts, setAlerts] = useState<ComplianceAlert[]>([]);
  const [ifta, setIfta] = useState<IftaReturn[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) { router.replace("/login"); return; }
    if (!user) return;

    Promise.all([
      api.get<ComplianceAlert[]>("/api/compliance/scan").catch(() => []),
      api.get<IftaReturn[]>("/api/compliance/ifta").catch(() => []),
    ]).then(([a, i]) => {
      setAlerts(a);
      setIfta(i);
    }).finally(() => setLoading(false));
  }, [user, authLoading, router]);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  const criticalAlerts = alerts.filter((a) => a.severity === "critical");
  const warningAlerts = alerts.filter((a) => a.severity !== "critical");

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Compliance</h1>

      {/* Alerts */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Fleet Scan</h2>
        {alerts.length === 0 ? (
          <div className="flex items-center gap-2 p-4 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="text-green-600" size={20} />
            <span className="text-sm text-green-800">All clear — no compliance issues found.</span>
          </div>
        ) : (
          <div className="space-y-3">
            {criticalAlerts.map((alert, i) => (
              <div key={i} className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                <AlertTriangle className="text-red-600 mt-0.5" size={18} />
                <div>
                  <p className="text-sm font-medium text-red-800">{alert.alert_type.replace(/_/g, " ")}</p>
                  <p className="text-sm text-red-700">{alert.message}</p>
                  <p className="text-xs text-red-500 mt-1">{alert.entity_label}</p>
                </div>
              </div>
            ))}
            {warningAlerts.map((alert, i) => (
              <div key={i} className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <AlertTriangle className="text-yellow-600 mt-0.5" size={18} />
                <div>
                  <p className="text-sm font-medium text-yellow-800">{alert.alert_type.replace(/_/g, " ")}</p>
                  <p className="text-sm text-yellow-700">{alert.message}</p>
                  <p className="text-xs text-yellow-500 mt-1">{alert.entity_label}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* IFTA */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">IFTA Returns</h2>
        {ifta.length === 0 ? (
          <p className="text-sm text-gray-500">No IFTA returns filed yet.</p>
        ) : (
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Miles</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Gallons</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {ifta.map((r) => (
                  <tr key={r.id}>
                    <td className="px-6 py-4 text-sm">{r.year} Q{r.quarter}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.status === "filed" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-right">{r.total_miles.toLocaleString()}</td>
                    <td className="px-6 py-4 text-sm text-right">{r.total_gallons.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
