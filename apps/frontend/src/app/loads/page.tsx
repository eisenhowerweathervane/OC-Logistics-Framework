"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import LoadStatusBadge from "@/components/load-status-badge";
import DataTable from "@/components/data-table";
import type { Load } from "@/lib/types";

const STATUSES = [
  "", "quoted", "booked", "dispatched", "arrived_pickup", "loaded",
  "in_transit", "arrived_delivery", "delivered", "invoice_ready",
  "invoiced", "paid", "closed", "archived",
];

export default function LoadsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [loads, setLoads] = useState<Load[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
      return;
    }
    if (!user) return;

    let cancelled = false;
    const params = statusFilter ? `?status=${statusFilter}` : "";
    api
      .get<Load[]>(`/api/loads${params}`)
      .then((data) => { if (!cancelled) setLoads(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user, authLoading, router, statusFilter]);

  const columns = [
    {
      key: "reference_number",
      header: "Reference",
      render: (load: Load) => load.reference_number || "-",
    },
    {
      key: "commodity",
      header: "Commodity",
      render: (load: Load) => load.commodity || "-",
    },
    {
      key: "status",
      header: "Status",
      render: (load: Load) => <LoadStatusBadge status={load.status} />,
    },
    {
      key: "rate_total",
      header: "Rate",
      render: (load: Load) =>
        load.rate_total ? `$${Number(load.rate_total).toLocaleString()}` : "-",
    },
    {
      key: "miles_loaded",
      header: "Miles",
      render: (load: Load) => load.miles_loaded ?? "-",
    },
    {
      key: "created_at",
      header: "Created",
      render: (load: Load) => new Date(load.created_at).toLocaleDateString(),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Loads</h1>
        <Link
          href="/loads/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
        >
          <Plus size={16} /> New Load
        </Link>
      </div>

      <div className="mb-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
        >
          <option value="">All statuses</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DataTable
          columns={columns}
          data={loads}
          onRowClick={(load) =>
            router.push(`/loads/${load.id}`)
          }
          emptyMessage="No loads found"
        />
      )}
    </div>
  );
}
