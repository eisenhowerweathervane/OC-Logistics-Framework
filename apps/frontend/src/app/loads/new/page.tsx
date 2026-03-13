"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Broker, Load } from "@/lib/types";

interface StopInput {
  seq: number;
  stop_type: string;
  facility_name: string;
  city: string;
  state: string;
}

export default function NewLoadPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    broker_id: "",
    reference_number: "",
    commodity: "",
    rate_total: "",
    miles_loaded: "",
    miles_deadhead_est: "",
  });

  const [stops, setStops] = useState<StopInput[]>([
    { seq: 1, stop_type: "pickup", facility_name: "", city: "", state: "" },
    { seq: 2, stop_type: "delivery", facility_name: "", city: "", state: "" },
  ]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
      return;
    }
    if (!user) return;
    api.get<Broker[]>("/api/brokers").then(setBrokers).catch(() => {});
  }, [user, authLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const body = {
        broker_id: form.broker_id || undefined,
        reference_number: form.reference_number || undefined,
        commodity: form.commodity || undefined,
        rate_total: form.rate_total ? Number(form.rate_total) : undefined,
        miles_loaded: form.miles_loaded ? Number(form.miles_loaded) : undefined,
        miles_deadhead_est: form.miles_deadhead_est
          ? Number(form.miles_deadhead_est)
          : undefined,
        stops: stops.map((s) => ({
          seq: s.seq,
          stop_type: s.stop_type,
          facility_name: s.facility_name || undefined,
          city: s.city || undefined,
          state: s.state || undefined,
        })),
      };

      const load = await api.post<Load>("/api/loads", body);
      router.push(`/loads/${load.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create load");
    } finally {
      setSubmitting(false);
    }
  };

  const updateStop = (idx: number, field: keyof StopInput, value: string) => {
    setStops((prev) =>
      prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)),
    );
  };

  return (
    <div className="max-w-2xl">
      <button
        onClick={() => router.push("/loads")}
        className="text-sm text-blue-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to loads
      </button>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Load</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Load Details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Broker
              </label>
              <select
                value={form.broker_id}
                onChange={(e) =>
                  setForm({ ...form, broker_id: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
              >
                <option value="">No broker</option>
                {brokers.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.legal_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reference #
              </label>
              <input
                value={form.reference_number}
                onChange={(e) =>
                  setForm({ ...form, reference_number: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Commodity
              </label>
              <input
                value={form.commodity}
                onChange={(e) =>
                  setForm({ ...form, commodity: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rate ($)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.rate_total}
                onChange={(e) =>
                  setForm({ ...form, rate_total: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Loaded Miles
              </label>
              <input
                type="number"
                min="0"
                value={form.miles_loaded}
                onChange={(e) =>
                  setForm({ ...form, miles_loaded: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Deadhead Miles
              </label>
              <input
                type="number"
                min="0"
                value={form.miles_deadhead_est}
                onChange={(e) =>
                  setForm({ ...form, miles_deadhead_est: e.target.value })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg border p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Stops</h2>
          <div className="space-y-4">
            {stops.map((stop, idx) => (
              <div key={idx} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-sm font-medium text-gray-500">
                    Stop #{stop.seq}
                  </span>
                  <select
                    value={stop.stop_type}
                    onChange={(e) => updateStop(idx, "stop_type", e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded text-sm bg-white"
                  >
                    <option value="pickup">Pickup</option>
                    <option value="delivery">Delivery</option>
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <input
                    placeholder="Facility name"
                    value={stop.facility_name}
                    onChange={(e) => updateStop(idx, "facility_name", e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                  <input
                    placeholder="City"
                    value={stop.city}
                    onChange={(e) => updateStop(idx, "city", e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                  <input
                    placeholder="State"
                    maxLength={2}
                    value={stop.state}
                    onChange={(e) =>
                      updateStop(idx, "state", e.target.value.toUpperCase())
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md text-sm"
                  />
                </div>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() =>
              setStops([
                ...stops,
                {
                  seq: stops.length + 1,
                  stop_type: "delivery",
                  facility_name: "",
                  city: "",
                  state: "",
                },
              ])
            }
            className="mt-3 text-sm text-blue-600 hover:underline"
          >
            + Add stop
          </button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="px-6 py-2 bg-blue-600 text-white rounded-md font-medium text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Creating..." : "Create Load"}
        </button>
      </form>
    </div>
  );
}
