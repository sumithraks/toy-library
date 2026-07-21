"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Toy } from "@/lib/types";

export function ToyDetail({ toyId }: { toyId: string }) {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pickupDate, setPickupDate] = useState("");

  const { data: toy, isLoading } = useQuery({
    queryKey: ["toy", toyId],
    queryFn: () => apiFetch<Toy>(`/toys/${toyId}/`),
  });

  const reset = () => {
    setMessage("");
    setError("");
  };

  const reserve = async () => {
    reset();
    if (!pickupDate) {
      setError("Choose a pickup date first");
      return;
    }
    try {
      await apiFetch("/reservations/", {
        method: "POST",
        body: { toy: toyId, pickup_by_date: pickupDate },
      });
      setMessage("Reserved! Check your reservations page for pickup details.");
      queryClient.invalidateQueries({ queryKey: ["toy", toyId] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reserve this toy");
    }
  };

  const joinWaitlist = async () => {
    reset();
    try {
      await apiFetch("/waitlist/", { method: "POST", body: { toy: toyId } });
      setMessage("Added to the waitlist. We'll notify you when it's available.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not join the waitlist");
    }
  };

  if (isLoading) return <p className="text-gray-500">Loading…</p>;
  if (!toy) return <p className="text-red-600">Toy not found.</p>;

  const maxDate = new Date();
  maxDate.setDate(maxDate.getDate() + 2);

  return (
    <div className="max-w-lg space-y-4 rounded-lg border bg-white p-6">
      <div>
        <h1 className="text-xl font-semibold">{toy.model_name}</h1>
        <p className="text-gray-500">{toy.make}</p>
      </div>
      <p className="text-sm text-gray-700">{toy.description || "No description provided."}</p>
      <div className="text-sm text-gray-500">
        <p>Status: {toy.status.replace("_", " ")}</p>
        {toy.min_age_years != null && <p>Recommended age: {toy.min_age_years}+</p>}
      </div>

      {toy.status === "AVAILABLE" && (
        <div className="space-y-2 border-t pt-4">
          <label className="block text-sm font-medium text-gray-700">
            Pick up by (within 2 days)
          </label>
          <input
            type="date"
            value={pickupDate}
            max={maxDate.toISOString().slice(0, 10)}
            onChange={(e) => setPickupDate(e.target.value)}
            className="rounded border px-3 py-2 text-sm"
          />
          <button
            onClick={reserve}
            className="block rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Reserve this toy
          </button>
        </div>
      )}

      {toy.status !== "AVAILABLE" && toy.status !== "RETIRED" && toy.status !== "BROKEN" && (
        <div className="border-t pt-4">
          <button
            onClick={joinWaitlist}
            className="rounded border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Join waitlist
          </button>
        </div>
      )}

      {message && <p className="text-sm text-green-600">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
