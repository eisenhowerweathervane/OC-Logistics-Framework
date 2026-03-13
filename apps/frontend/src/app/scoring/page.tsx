"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LaneProfitability, BrokerRating } from "@/lib/types";

const GRADE_COLORS: Record<string, string> = {
  A: "bg-green-100 text-green-800",
  B: "bg-blue-100 text-blue-800",
  C: "bg-yellow-100 text-yellow-800",
  D: "bg-orange-100 text-orange-800",
  F: "bg-red-100 text-red-800",
};

export default function ScoringPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [lanes, setLanes] = useState<LaneProfitability[]>([]);
  const [brokers, setBrokers] = useState<BrokerRating[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) { router.replace("/login"); return; }
    if (!user) return;

    Promise.all([
      api.get<LaneProfitability[]>("/api/scoring/lanes").catch(() => []),
      api.get<BrokerRating[]>("/api/scoring/brokers").catch(() => []),
    ]).then(([l, b]) => {
      setLanes(l);
      setBrokers(b);
    }).finally(() => setLoading(false));
  }, [user, authLoading, router]);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Scoring</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lane Profitability */}
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Lane Profitability</h2>
          {lanes.length > 0 ? (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Lane</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Loads</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Avg RPM</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {lanes.map((l, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3 text-sm font-medium">{l.origin_state} &rarr; {l.dest_state}</td>
                    <td className="px-4 py-3 text-sm text-right">{l.loads_count}</td>
                    <td className="px-4 py-3 text-sm text-right">${l.avg_rpm.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-right">${l.total_revenue.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-gray-500">No lane data yet. Deliver some loads to see profitability.</p>
          )}
        </div>

        {/* Broker Ratings */}
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Broker Ratings</h2>
          {brokers.length > 0 ? (
            <div className="space-y-3">
              {brokers.map((b) => {
                const grade = b.score >= 90 ? "A" : b.score >= 75 ? "B" : b.score >= 60 ? "C" : b.score >= 40 ? "D" : "F";
                return (
                  <div key={b.broker_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium">{b.broker_name}</p>
                      <p className="text-xs text-gray-500">{b.loads_count} loads | Avg RPM: ${b.avg_rpm.toFixed(2)}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${GRADE_COLORS[grade] || "bg-gray-100"}`}>
                      {grade}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No broker data yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
