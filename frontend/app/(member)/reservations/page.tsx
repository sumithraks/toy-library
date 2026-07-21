"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Paginated, Reservation } from "@/lib/types";
import { useState } from "react";

export default function ReservationsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");

  const { data } = useQuery({
    queryKey: ["my-reservations-all"],
    queryFn: () => apiFetch<Paginated<Reservation>>("/reservations/"),
  });

  const cancel = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/reservations/${id}/cancel/`, { method: "POST" });
      queryClient.invalidateQueries({ queryKey: ["my-reservations-all"] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not cancel");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">My reservations</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="rounded-lg border bg-white p-4">
        {data?.results.length ? (
          <ul className="divide-y">
            {data.results.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-medium">Status: {r.status}</p>
                  <p className="text-gray-500">
                    Pick up by {new Date(r.pickup_deadline).toLocaleString()}
                  </p>
                </div>
                {r.status === "ACTIVE" && (
                  <button
                    onClick={() => cancel(r.id)}
                    className="rounded border px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No reservations yet.</p>
        )}
      </div>
    </div>
  );
}
