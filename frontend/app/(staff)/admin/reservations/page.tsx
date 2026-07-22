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

  const STATUS_LABELS: Record<Reservation["status"], string> = {
    ACTIVE: "Active",
    PICKED_UP: "Picked up",
    EXPIRED: "Expired",
    CANCELLED: "Cancelled",
  };

  const checkOut = async (id: string) => {
    if (confirmingIds.has(id)) return;
    setError("");
    setConfirmingIds((prev) => new Set(prev).add(id));
    try {
      const updated = await apiFetch<Reservation>(`/reservations/${id}/confirm-pickup/`, {
        method: "POST",
      });
      queryClient.setQueryData<Paginated<Reservation>>(["admin-reservations"], (old) =>
        old
          ? { ...old, results: old.results.map((r) => (r.id === id ? updated : r)) }
          : old
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not check out toy");
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
              <th className="p-2">Status</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="p-2 font-mono text-xs">{r.toy}</td>
                <td className="p-2 font-mono text-xs">{r.user}</td>
                <td className="p-2">{new Date(r.pickup_deadline).toLocaleString()}</td>
                <td className="p-2">{STATUS_LABELS[r.status]}</td>
                <td className="p-2">
                  {r.status === "ACTIVE" && (
                    <button
                      onClick={() => checkOut(r.id)}
                      disabled={confirmingIds.has(r.id)}
                      className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {confirmingIds.has(r.id) ? "Checking out…" : "Check out"}
                    </button>
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
