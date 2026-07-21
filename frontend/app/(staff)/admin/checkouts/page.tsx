"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { CheckoutRecord, Paginated } from "@/lib/types";

function AdminCheckoutsInner() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [form, setForm] = useState({ toy: "", member: "" });
  const [returning, setReturning] = useState<Record<string, { condition: string }>>({});

  useEffect(() => {
    const toyId = searchParams.get("toy");
    if (toyId) setForm((f) => ({ ...f, toy: toyId }));
  }, [searchParams]);

  const { data } = useQuery({
    queryKey: ["admin-checkouts"],
    queryFn: () => apiFetch<Paginated<CheckoutRecord>>("/checkouts/"),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-checkouts"] });

  const createCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await apiFetch("/checkouts/", { method: "POST", body: form });
      setForm({ toy: "", member: "" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not check out");
    }
  };

  const returnCheckout = async (id: string) => {
    setError("");
    const condition = returning[id]?.condition || "LIGHTLY_USED";
    try {
      await apiFetch(`/checkouts/${id}/return/`, {
        method: "POST",
        body: {
          condition,
          damaged_status: condition === "DAMAGED" ? "UNDER_REPAIR" : undefined,
        },
      });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not return");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Checkouts</h1>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      <form onSubmit={createCheckout} className="flex flex-wrap items-end gap-2 rounded-lg border bg-white p-4">
        <div>
          <label className="block text-xs text-gray-500">Toy ID</label>
          <input
            required
            value={form.toy}
            onChange={(e) => setForm({ ...form, toy: e.target.value })}
            className="rounded border px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500">Member ID</label>
          <input
            required
            value={form.member}
            onChange={(e) => setForm({ ...form, member: e.target.value })}
            className="rounded border px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          className="rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Check out
        </button>
      </form>

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="p-2">Toy</th>
              <th className="p-2">Member</th>
              <th className="p-2">Due</th>
              <th className="p-2">Status</th>
              <th className="p-2">Return</th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((c) => (
              <tr key={c.id} className="border-t">
                <td className="p-2 font-mono text-xs">{c.toy}</td>
                <td className="p-2 font-mono text-xs">{c.member}</td>
                <td className="p-2">{c.current_due_date}</td>
                <td className="p-2">{c.status}</td>
                <td className="p-2">
                  {c.status !== "RETURNED" && (
                    <div className="flex items-center gap-1">
                      <select
                        value={returning[c.id]?.condition || "LIGHTLY_USED"}
                        onChange={(e) => setReturning({ ...returning, [c.id]: { condition: e.target.value } })}
                        className="rounded border px-1 py-1 text-xs"
                      >
                        <option value="NEW">New</option>
                        <option value="LIGHTLY_USED">Lightly used</option>
                        <option value="USED">Used</option>
                        <option value="DAMAGED">Damaged</option>
                      </select>
                      <button
                        onClick={() => returnCheckout(c.id)}
                        className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                      >
                        Return
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function AdminCheckoutsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading…</div>}>
      <AdminCheckoutsInner />
    </Suspense>
  );
}
