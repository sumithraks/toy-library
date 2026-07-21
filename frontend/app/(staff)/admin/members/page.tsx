"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { Membership, MembershipTier, Paginated } from "@/lib/types";

export default function AdminMembersPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [tierChoice, setTierChoice] = useState<Record<string, string>>({});
  const [refundForm, setRefundForm] = useState<Record<string, { amount_returned: string; notes: string }>>(
    {}
  );
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});

  const { data } = useQuery({
    queryKey: ["admin-memberships"],
    queryFn: () => apiFetch<Paginated<Membership>>("/memberships/"),
  });

  const { data: tiers } = useQuery({
    queryKey: ["membership-tiers"],
    queryFn: () => apiFetch<Paginated<MembershipTier>>("/memberships/tiers/", { auth: false }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-memberships"] });

  const activate = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/memberships/${id}/activate/`, { method: "POST" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not activate");
    }
  };

  const changeTier = async (id: string) => {
    setError("");
    const newTierCode = tierChoice[id];
    if (!newTierCode) return;
    try {
      await apiFetch(`/memberships/${id}/change-tier/`, {
        method: "POST",
        body: { new_tier_code: newTierCode },
      });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not change tier");
    }
  };

  const requestTermination = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/memberships/${id}/request-termination/`, { method: "POST" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not request termination");
    }
  };

  const approveTermination = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/memberships/${id}/approve-termination/`, {
        method: "POST",
        body: { approve: true },
      });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve termination");
    }
  };

  const rejectTermination = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/memberships/${id}/approve-termination/`, {
        method: "POST",
        body: { approve: false, reason: rejectReason[id] || "" },
      });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject termination");
    }
  };

  const refundDeposit = async (id: string) => {
    setError("");
    const values = refundForm[id] || { amount_returned: "0", notes: "" };
    try {
      await apiFetch(`/memberships/${id}/refund-deposit/`, {
        method: "POST",
        body: { amount_returned: Number(values.amount_returned), notes: values.notes },
      });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not refund deposit");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Members</h1>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      <div className="space-y-3">
        {data?.results.map((m) => (
          <div key={m.id} className="rounded-lg border bg-white p-4 text-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {m.tier.name} — {m.status}
                </p>
                <p className="text-xs text-gray-400">User: {m.user}</p>
                {m.renewed_through && <p className="text-gray-500">Renews through {m.renewed_through}</p>}
              </div>
              {m.status === "PENDING_PAYMENT" && (
                <button
                  onClick={() => activate(m.id)}
                  className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                >
                  Activate (fees collected)
                </button>
              )}
            </div>

            {m.status === "ACTIVE" && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
                <select
                  value={tierChoice[m.id] ?? ""}
                  onChange={(e) => setTierChoice({ ...tierChoice, [m.id]: e.target.value })}
                  className="rounded border px-2 py-1 text-xs"
                >
                  <option value="">Change tier…</option>
                  {tiers?.results
                    .filter((t) => t.code !== m.tier.code)
                    .map((t) => (
                      <option key={t.code} value={t.code}>
                        {t.name}
                      </option>
                    ))}
                </select>
                <button
                  onClick={() => changeTier(m.id)}
                  className="rounded border px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  Apply tier change
                </button>
                <button
                  onClick={() => requestTermination(m.id)}
                  className="ml-auto rounded bg-gray-700 px-3 py-1 text-xs font-medium text-white hover:bg-gray-800"
                >
                  Request termination
                </button>
              </div>
            )}

            {m.sign_off?.status === "REQUESTED" && (
              <div className="mt-3 space-y-2 border-t pt-3">
                <p className="text-xs text-gray-500">
                  Termination requested — deposit due: ${m.sign_off.deposit_amount_due}
                </p>
                {user?.role === "ADMIN" ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      placeholder="Rejection reason (if rejecting)"
                      value={rejectReason[m.id] ?? ""}
                      onChange={(e) => setRejectReason({ ...rejectReason, [m.id]: e.target.value })}
                      className="flex-1 rounded border px-2 py-1 text-xs"
                    />
                    <button
                      onClick={() => approveTermination(m.id)}
                      className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => rejectTermination(m.id)}
                      className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">Waiting for an admin to approve or reject.</p>
                )}
              </div>
            )}

            {m.sign_off?.status === "APPROVED" && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
                <input
                  placeholder="Amount returned"
                  type="number"
                  step="0.01"
                  value={refundForm[m.id]?.amount_returned ?? ""}
                  onChange={(e) =>
                    setRefundForm({
                      ...refundForm,
                      [m.id]: {
                        amount_returned: e.target.value,
                        notes: refundForm[m.id]?.notes || "",
                      },
                    })
                  }
                  className="w-32 rounded border px-2 py-1 text-xs"
                />
                <input
                  placeholder="Deduction notes (if less than deposit)"
                  value={refundForm[m.id]?.notes ?? ""}
                  onChange={(e) =>
                    setRefundForm({
                      ...refundForm,
                      [m.id]: {
                        amount_returned: refundForm[m.id]?.amount_returned || "0",
                        notes: e.target.value,
                      },
                    })
                  }
                  className="flex-1 rounded border px-2 py-1 text-xs"
                />
                <button
                  onClick={() => refundDeposit(m.id)}
                  className="rounded bg-gray-700 px-3 py-1 text-xs font-medium text-white hover:bg-gray-800"
                >
                  Refund deposit
                </button>
              </div>
            )}

            {m.sign_off?.status === "REJECTED" && (
              <p className="mt-3 border-t pt-3 text-xs text-red-600">
                Termination rejected: {m.sign_off.rejection_reason || "No reason given"}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
