"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { LedgerEntry, Paginated } from "@/lib/types";

export default function AdminBillingPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");

  const { data } = useQuery({
    queryKey: ["admin-ledger"],
    queryFn: () => apiFetch<Paginated<LedgerEntry>>("/ledger-entries/?status=PENDING"),
  });

  const markPaid = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/ledger-entries/${id}/mark-paid/`, { method: "POST" });
      queryClient.invalidateQueries({ queryKey: ["admin-ledger"] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not mark paid");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Pending charges</h1>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="p-2">User</th>
              <th className="p-2">Type</th>
              <th className="p-2">Direction</th>
              <th className="p-2">Amount</th>
              <th className="p-2">Notes</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((entry) => (
              <tr key={entry.id} className="border-t">
                <td className="p-2 font-mono text-xs">{entry.user}</td>
                <td className="p-2">{entry.entry_type.replace(/_/g, " ")}</td>
                <td className="p-2">{entry.direction}</td>
                <td className="p-2">${entry.amount}</td>
                <td className="max-w-xs truncate p-2 text-xs text-gray-500">{entry.notes}</td>
                <td className="p-2">
                  <button
                    onClick={() => markPaid(entry.id)}
                    className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                  >
                    Mark paid
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.results.length === 0 && (
          <p className="p-4 text-sm text-gray-500">No pending charges.</p>
        )}
      </div>
    </div>
  );
}
