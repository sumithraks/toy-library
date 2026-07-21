"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { Paginated, User } from "@/lib/types";

export default function AdminStaffPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [form, setForm] = useState({ email: "", first_name: "", last_name: "" });

  const { data } = useQuery({
    queryKey: ["admin-staff-users"],
    queryFn: () => apiFetch<Paginated<User>>("/auth/staff/"),
    enabled: user?.role === "ADMIN",
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-staff-users"] });

  if (user && user.role !== "ADMIN") {
    return <p className="rounded bg-yellow-50 p-4 text-sm text-yellow-800">Admins only.</p>;
  }

  const createStaff = async () => {
    setError("");
    try {
      await apiFetch("/auth/staff/", { method: "POST", body: form });
      setForm({ email: "", first_name: "", last_name: "" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create staff account");
    }
  };

  const deactivate = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/auth/staff/${id}/deactivate/`, { method: "POST" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not deactivate");
    }
  };

  const reactivate = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/auth/staff/${id}/reactivate/`, { method: "POST" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reactivate");
    }
  };

  const setRole = async (id: string, role: "STAFF" | "ADMIN") => {
    setError("");
    try {
      await apiFetch(`/auth/staff/${id}/set-role/`, { method: "POST", body: { role } });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change role");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Staff</h1>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-white p-4">
        <input
          placeholder="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="w-56 rounded border px-2 py-1 text-sm"
        />
        <input
          placeholder="First name"
          value={form.first_name}
          onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          className="w-36 rounded border px-2 py-1 text-sm"
        />
        <input
          placeholder="Last name"
          value={form.last_name}
          onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          className="w-36 rounded border px-2 py-1 text-sm"
        />
        <button
          onClick={createStaff}
          className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
        >
          Add staff
        </button>
      </div>

      <div className="space-y-3">
        {data?.results.map((u) => (
          <div key={u.id} className="rounded-lg border bg-white p-4 text-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {u.first_name} {u.last_name} — {u.email}
                </p>
                <p className="text-xs text-gray-400">
                  {u.role} — {u.is_active ? "Active" : "Deactivated"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {u.role === "STAFF" && (
                  <button
                    onClick={() => setRole(u.id, "ADMIN")}
                    className="rounded border px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Promote to admin
                  </button>
                )}
                {u.role === "ADMIN" && u.id !== user?.id && (
                  <button
                    onClick={() => setRole(u.id, "STAFF")}
                    className="rounded border px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Demote to staff
                  </button>
                )}
                {u.is_active ? (
                  <button
                    onClick={() => deactivate(u.id)}
                    className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
                  >
                    Deactivate
                  </button>
                ) : (
                  <button
                    onClick={() => reactivate(u.id)}
                    className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                  >
                    Reactivate
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
