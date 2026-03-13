"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Receivable } from "@/lib/types";

export default function ReceivablesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [loading, setLoading] = useState(true);
  const [showOverdueOnly, setShowOverdueOnly] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) { router.replace("/login"); return; }
    if (!user) return;

    let cancelled = false;
    const params = showOverdueOnly ? "?overdue_only=true" : "";
    api.get<Receivable[]>(`/api/receivables${params}`)
      .then((data) => { if (!cancelled) setReceivables(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user, authLoading, router, showOverdueOnly]);

  const now = new Date();
  const totalOutstanding = receivables
    .filter((r) => r.status !== "paid")
    .reduce((sum, r) => sum + Number(r.amount), 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Receivables</h1>
          <p className="text-sm text-gray-500 mt-1">
            Outstanding: ${totalOutstanding.toLocaleString()}
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showOverdueOnly}
            onChange={(e) => setShowOverdueOnly(e.target.checked)}
            className="rounded border-gray-300"
          />
          Overdue only
        </label>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : receivables.length === 0 ? (
        <div className="text-center py-12 text-gray-500 bg-white rounded-lg border">
          No receivables found.
        </div>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Load</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {receivables.map((r) => {
                const isOverdue =
                  r.status !== "paid" && new Date(r.due_date) < now;
                return (
                  <tr
                    key={r.id}
                    className={isOverdue ? "bg-red-50" : ""}
                    onClick={() => router.push(`/loads/${r.load_id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td className="px-6 py-4 text-sm font-medium text-blue-600">
                      {r.load_id.slice(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-sm text-right">
                      ${Number(r.amount).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {new Date(r.due_date).toLocaleDateString()}
                      {isOverdue && (
                        <span className="ml-2 text-xs text-red-600 font-medium">
                          OVERDUE
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          r.status === "paid"
                            ? "bg-green-100 text-green-700"
                            : r.status === "partial"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
