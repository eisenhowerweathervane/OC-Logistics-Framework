"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import DataTable from "@/components/data-table";
import type { Vehicle } from "@/lib/types";

export default function VehiclesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ unit_number: "", make: "", model: "", year: "" });
  const [submitting, setSubmitting] = useState(false);

  const fetchVehicles = () => {
    api.get<Vehicle[]>("/api/vehicles")
      .then(setVehicles)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!authLoading && !user) { router.replace("/login"); return; }
    if (!user) return;
    fetchVehicles();
  }, [user, authLoading, router]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/api/vehicles", {
        unit_number: form.unit_number,
        make: form.make || undefined,
        model: form.model || undefined,
        year: form.year ? Number(form.year) : undefined,
      });
      setForm({ unit_number: "", make: "", model: "", year: "" });
      setShowForm(false);
      fetchVehicles();
    } catch {
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    { key: "unit_number", header: "Unit #" },
    { key: "make", header: "Make", render: (v: Vehicle) => v.make || "-" },
    { key: "model", header: "Model", render: (v: Vehicle) => v.model || "-" },
    { key: "year", header: "Year", render: (v: Vehicle) => v.year ?? "-" },
    {
      key: "status",
      header: "Status",
      render: (v: Vehicle) => (
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${v.status === "available" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
          {v.status}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Vehicles</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
        >
          <Plus size={16} /> Add Vehicle
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg border p-4 mb-6 flex gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Unit #</label>
            <input required value={form.unit_number} onChange={(e) => setForm({ ...form, unit_number: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Make</label>
            <input value={form.make} onChange={(e) => setForm({ ...form, make: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Model</label>
            <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Year</label>
            <input type="number" min="1900" max="2100" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} className="px-3 py-2 border border-gray-300 rounded-md text-sm w-24" />
          </div>
          <button type="submit" disabled={submitting} className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50">
            {submitting ? "Saving..." : "Save"}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DataTable columns={columns} data={vehicles} emptyMessage="No vehicles found" />
      )}
    </div>
  );
}
