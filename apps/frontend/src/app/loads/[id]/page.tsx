"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import LoadStatusBadge from "@/components/load-status-badge";
import type { Load, InvoicePacket } from "@/lib/types";
import { VALID_TRANSITIONS } from "@/lib/types";

export default function LoadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [load, setLoad] = useState<Load | null>(null);
  const [packet, setPacket] = useState<InvoicePacket | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
      return;
    }
    if (!user) return;

    Promise.all([
      api.get<Load>(`/api/loads/${id}`),
      api.get<InvoicePacket>(`/api/loads/${id}/invoice-packet`).catch(() => null),
    ])
      .then(([l, p]) => {
        setLoad(l);
        setPacket(p);
      })
      .catch(() => router.replace("/loads"))
      .finally(() => setLoading(false));
  }, [id, user, authLoading, router]);

  const handleTransition = async (newStatus: string) => {
    setTransitioning(true);
    try {
      await api.post(`/api/loads/${id}/status-events`, {
        status: newStatus,
        occurred_at: new Date().toISOString(),
      });
      const updated = await api.get<Load>(`/api/loads/${id}`);
      setLoad(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Transition failed");
    } finally {
      setTransitioning(false);
    }
  };

  const handleGenerateInvoice = async () => {
    try {
      const p = await api.post<InvoicePacket>(
        `/api/loads/${id}/invoice-packet/generate`,
      );
      setPacket(p);
      const updated = await api.get<Load>(`/api/loads/${id}`);
      setLoad(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to generate invoice");
    }
  };

  if (loading || !load) {
    return <p className="text-gray-500">Loading...</p>;
  }

  const nextStatuses = VALID_TRANSITIONS[load.status] || [];

  return (
    <div className="max-w-4xl">
      <button
        onClick={() => router.push("/loads")}
        className="text-sm text-blue-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to loads
      </button>

      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {load.reference_number || `Load ${load.id.slice(0, 8)}`}
        </h1>
        <LoadStatusBadge status={load.status} />
      </div>

      {/* State machine actions */}
      {nextStatuses.length > 0 && (
        <div className="bg-white rounded-lg border p-4 mb-6">
          <p className="text-sm text-gray-500 mb-2">Available transitions:</p>
          <div className="flex gap-2 flex-wrap">
            {nextStatuses.map((s) => (
              <button
                key={s}
                onClick={() => handleTransition(s)}
                disabled={transitioning}
                className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {s.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Load details */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-900 mb-3">Details</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Commodity</dt>
              <dd>{load.commodity || "-"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Rate</dt>
              <dd>
                {load.rate_total
                  ? `$${Number(load.rate_total).toLocaleString()}`
                  : "-"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Miles</dt>
              <dd>{load.miles_loaded ?? "-"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Weight</dt>
              <dd>
                {load.weight_lbs
                  ? `${Number(load.weight_lbs).toLocaleString()} lbs`
                  : "-"}
              </dd>
            </div>
          </dl>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-900 mb-3">Invoice</h2>
          {packet ? (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Status</dt>
                <dd className="font-medium">{packet.status}</dd>
              </div>
              {packet.generated_at && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Generated</dt>
                  <dd>{new Date(packet.generated_at).toLocaleDateString()}</dd>
                </div>
              )}
            </dl>
          ) : (
            <div>
              <p className="text-sm text-gray-500 mb-2">No invoice packet yet.</p>
              {load.status === "delivered" && (
                <button
                  onClick={handleGenerateInvoice}
                  className="px-3 py-1.5 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                >
                  Generate Invoice
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Stops */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <h2 className="font-semibold text-gray-900 mb-3">Stops</h2>
        <div className="space-y-3">
          {load.stops
            .sort((a, b) => a.seq - b.seq)
            .map((stop) => (
              <div
                key={stop.id}
                className="flex items-center gap-4 p-3 bg-gray-50 rounded"
              >
                <span className="text-xs font-medium text-gray-500 w-6">
                  #{stop.seq}
                </span>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded ${
                    stop.stop_type === "pickup"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-green-100 text-green-700"
                  }`}
                >
                  {stop.stop_type}
                </span>
                <div className="text-sm">
                  <p className="font-medium">{stop.facility_name || "TBD"}</p>
                  <p className="text-gray-500">
                    {[stop.city, stop.state].filter(Boolean).join(", ") || "No location"}
                  </p>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Assignments */}
      {load.assignments.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="font-semibold text-gray-900 mb-3">Assignments</h2>
          <div className="space-y-2 text-sm">
            {load.assignments.map((a) => (
              <div key={a.id} className="flex justify-between p-2 bg-gray-50 rounded">
                <span>Driver: {a.driver_id.slice(0, 8)}...</span>
                <span className="text-gray-500">
                  {new Date(a.assigned_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
