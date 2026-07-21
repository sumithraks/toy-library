"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { LedgerEntry, Membership, MembershipTier, Paginated } from "@/lib/types";

export default function MembershipPage() {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const { data: tiers } = useQuery({
    queryKey: ["membership-tiers"],
    queryFn: () => apiFetch<Paginated<MembershipTier>>("/memberships/tiers/", { auth: false }),
  });

  const { data: membership, refetch: refetchMembership } = useQuery({
    queryKey: ["my-membership-full"],
    queryFn: () => apiFetch<Membership>("/memberships/me/").catch(() => null),
  });

  const { data: ledger } = useQuery({
    queryKey: ["my-ledger"],
    queryFn: () => apiFetch<Paginated<LedgerEntry>>("/ledger-entries/?user=me"),
  });

  const reset = () => {
    setError("");
    setMessage("");
  };

  const joinTier = async (tierCode: string) => {
    reset();
    try {
      await apiFetch("/memberships/signup/", { method: "POST", body: { tier_code: tierCode } });
      setMessage("Signed up! Visit the library to pay your joining fee and deposit, then staff will activate your membership.");
      refetchMembership();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign up");
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Membership</h1>

      {message && <p className="rounded bg-green-50 p-2 text-sm text-green-700">{message}</p>}
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      {membership && (
        <section className="rounded-lg border bg-white p-4 text-sm">
          <p>
            Current tier: <span className="font-medium">{membership.tier.name}</span> — Status:{" "}
            <span className="font-medium">{membership.status}</span>
          </p>
          {membership.renewed_through && <p>Renews through {membership.renewed_through}</p>}
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {tiers?.results.map((tier) => (
          <div key={tier.id} className="rounded-lg border bg-white p-4">
            <h3 className="font-semibold">{tier.name}</h3>
            <p className="mt-1 text-sm text-gray-500">Joining fee: ${tier.joining_fee}</p>
            <p className="text-sm text-gray-500">Deposit: ${tier.deposit_amount}</p>
            <p className="text-sm text-gray-500">Renewal: ${tier.renewal_fee}/yr</p>
            <ul className="mt-2 text-xs text-gray-500">
              <li>{tier.max_concurrent_checkouts} toy(s) at a time</li>
              <li>{tier.loan_period_days}-day loans</li>
              <li>{tier.complimentary_extension_days}-day free extension</li>
            </ul>
            {!membership && (
              <button
                onClick={() => joinTier(tier.code)}
                className="mt-3 w-full rounded bg-blue-600 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Join
              </button>
            )}
          </div>
        ))}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-medium text-gray-700">Billing history</h2>
        {ledger?.results.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="pb-1">Type</th>
                <th className="pb-1">Amount</th>
                <th className="pb-1">Status</th>
                <th className="pb-1">Date</th>
              </tr>
            </thead>
            <tbody>
              {ledger.results.map((entry) => (
                <tr key={entry.id} className="border-t">
                  <td className="py-1">{entry.entry_type.replace(/_/g, " ")}</td>
                  <td className="py-1">
                    {entry.direction === "CHARGE" ? "-" : "+"}${entry.amount}
                  </td>
                  <td className="py-1">{entry.status}</td>
                  <td className="py-1">{new Date(entry.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-gray-500">No billing history yet.</p>
        )}
      </section>
    </div>
  );
}
