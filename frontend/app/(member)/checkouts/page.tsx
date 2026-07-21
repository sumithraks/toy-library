"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { CheckoutRecord, Paginated } from "@/lib/types";

function CheckoutRow({ checkout }: { checkout: CheckoutRecord }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [paidDays, setPaidDays] = useState(7);
  const [showPaid, setShowPaid] = useState(false);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["my-checkouts-all"] });

  const extendComplimentary = async () => {
    setError("");
    try {
      await apiFetch(`/checkouts/${checkout.id}/extend/complimentary/`, { method: "POST" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not extend");
    }
  };

  const requestPaidExtension = async () => {
    setError("");
    try {
      await apiFetch(`/checkouts/${checkout.id}/extend/paid/`, {
        method: "POST",
        body: { days: paidDays },
      });
      setShowPaid(false);
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not request extension");
    }
  };

  return (
    <li className="space-y-2 py-3">
      <div className="flex items-center justify-between text-sm">
        <div>
          <p className="font-medium">Due {checkout.current_due_date}</p>
          <p className="text-gray-500">Status: {checkout.status}</p>
        </div>
        <div className="flex gap-2">
          {checkout.complimentary_extension_available && checkout.status === "ACTIVE" && (
            <button
              onClick={extendComplimentary}
              className="rounded border border-green-600 px-3 py-1 text-xs font-medium text-green-700 hover:bg-green-50"
            >
              Extend for free
            </button>
          )}
          {checkout.status !== "RETURNED" && (
            <button
              onClick={() => setShowPaid((s) => !s)}
              className="rounded border px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
            >
              Pay to extend (5¢/day)
            </button>
          )}
        </div>
      </div>
      {showPaid && (
        <div className="flex items-center gap-2 rounded bg-gray-50 p-2 text-sm">
          <label>Days:</label>
          <input
            type="number"
            min={1}
            max={30}
            value={paidDays}
            onChange={(e) => setPaidDays(Number(e.target.value))}
            className="w-16 rounded border px-2 py-1"
          />
          <span className="text-gray-500">= ${(paidDays * 0.05).toFixed(2)}</span>
          <button
            onClick={requestPaidExtension}
            className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-700"
          >
            Request (pay at the library)
          </button>
        </div>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </li>
  );
}

export default function CheckoutsPage() {
  const { data } = useQuery({
    queryKey: ["my-checkouts-all"],
    queryFn: () => apiFetch<Paginated<CheckoutRecord>>("/checkouts/"),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">My checkouts</h1>
      <div className="rounded-lg border bg-white p-4">
        {data?.results.length ? (
          <ul className="divide-y">
            {data.results.map((c) => (
              <CheckoutRow key={c.id} checkout={c} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No checkout history yet.</p>
        )}
      </div>
    </div>
  );
}
