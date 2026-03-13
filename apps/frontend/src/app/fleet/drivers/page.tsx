"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import DataTable from "@/components/data-table";
import type { Driver } from "@/lib/types";

export default function DriversPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", phone: "" });
  const [submitting, setSubmitting] = useState(false);

  const fetchDrivers = () => {
    api.get<Driver[]>("/api/drivers")
      .then(setDrivers)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!authLoading && !user) { router.replace("/login"); return; }
    if (!user) return;
    fetchDrivers();
  }, [user, authLoading, router]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/api/drivers", {
        first_name: form.first_name,
        last_name: form.last_name,
        phone: form.phone || undefined,
      });
      setForm({ first_name: "", last_name: "", phone: "" });
      setShowForm(false);
      fetchDrivers();
    } catch {
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    { key: "first_name", header: "First Name" },
    { key: "last_name", header: "Last Name" },
    { key: "phone", header: "Phone", render: (d: Driver) => d.phone || "-" },
    { key: "license_state", header: "License", render: (d: Driver) => d.license_state || "-" },
    {
      key: "status",
      header: "Status",
      render: (d: Driver) => (
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${d.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
          {d.status}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Drivers</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
        >
          <Plus size={16} /> Add Driver
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-lg border p-4 mb-6 flex gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">First Name</label>
            <input
              required
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Last Name</label>
            <input
              required
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Phone</label>
            <input
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              placeholder="+15551234567"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Save"}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <DataTable
          columns={columns}
          data={drivers}
          emptyMessage="No drivers found"
        />
      )}
    </div>
  );
}
