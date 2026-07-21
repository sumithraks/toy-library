"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Paginated, Reservation } from "@/lib/types";

export default function AdminReservationsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [confirmingIds, setConfirmingIds] = useState<Set<string>>(new Set());

  const { data } = useQuery({
    queryKey: ["admin-reservations"],
    queryFn: () => apiFetch<Paginated<Reservation>>("/reservations/?status=ACTIVE"),
  });

  const confirmPickup = async (id: string) => {
    if (confirmingIds.has(id)) return;
    setError("");
    setConfirmingIds((prev) => new Set(prev).add(id));
    try {
      await apiFetch(`/reservations/${id}/confirm-pickup/`, { method: "POST" });
      queryClient.invalidateQueries({ queryKey: ["admin-reservations"] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not confirm pickup");
    } finally {
      setConfirmingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Pending pickups</h1>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="p-2">Toy</th>
              <th className="p-2">User</th>
              <th className="p-2">Pickup deadline</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="p-2 font-mono text-xs">{r.toy}</td>
                <td className="p-2 font-mono text-xs">{r.user}</td>
                <td className="p-2">{new Date(r.pickup_deadline).toLocaleString()}</td>
                <td className="p-2">
                  <button
                    onClick={() => confirmPickup(r.id)}
                    disabled={confirmingIds.has(r.id)}
                    className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {confirmingIds.has(r.id) ? "Confirming…" : "Confirm pickup"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
