"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";

type DonationItem = {
  id: string;
  item_type: string;
  description: string;
  make: string;
  model_name: string;
  age_rating: string;
  toy: string | null;
};

type Donation = {
  id: string;
  donor: { name: string; email: string };
  status: string;
  donated_at: string;
  items: DonationItem[];
};

export default function AdminDonationsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [intakeForm, setIntakeForm] = useState<Record<string, { condition: string; age_rating: string }>>(
    {}
  );

  const { data } = useQuery({
    queryKey: ["admin-donations"],
    queryFn: () => apiFetch<{ results: Donation[] }>("/donations/"),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-donations"] });

  const accept = async (id: string) => {
    setError("");
    try {
      await apiFetch(`/donations/${id}/accept/`, { method: "POST" });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not accept");
    }
  };

  const reject = async (id: string) => {
    setError("");
    const reason = window.prompt("Rejection reason?") || "";
    try {
      await apiFetch(`/donations/${id}/reject/`, { method: "POST", body: { reason } });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject");
    }
  };

  const completeIntake = async (donationId: string, itemId: string) => {
    setError("");
    const values = intakeForm[itemId] || { condition: "LIGHTLY_USED", age_rating: "" };
    try {
      await apiFetch(`/donations/${donationId}/items/${itemId}/complete-intake/`, {
        method: "POST",
        body: values,
      });
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not complete intake");
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Donations</h1>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      <div className="space-y-4">
        {data?.results.map((donation) => (
          <div key={donation.id} className="rounded-lg border bg-white p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{donation.donor.name}</p>
                <p className="text-sm text-gray-500">
                  {donation.status} · {new Date(donation.donated_at).toLocaleDateString()}
                </p>
              </div>
              {donation.status === "SUBMITTED" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => accept(donation.id)}
                    className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => reject(donation.id)}
                    className="rounded border px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>

            <ul className="mt-3 space-y-2">
              {donation.items.map((item) => (
                <li key={item.id} className="rounded bg-gray-50 p-2 text-sm">
                  <p>
                    {item.item_type} — {item.make} {item.model_name}
                  </p>
                  <p className="text-gray-500">{item.description}</p>
                  {!item.toy && (donation.status === "IN_INTAKE" || donation.status === "ACCEPTED") && (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <select
                        value={intakeForm[item.id]?.condition || "LIGHTLY_USED"}
                        onChange={(e) =>
                          setIntakeForm({
                            ...intakeForm,
                            [item.id]: {
                              ...intakeForm[item.id],
                              condition: e.target.value,
                              age_rating: intakeForm[item.id]?.age_rating || "",
                            },
                          })
                        }
                        className="rounded border px-2 py-1 text-xs"
                      >
                        <option value="NEW">New</option>
                        <option value="LIGHTLY_USED">Lightly used</option>
                        <option value="USED">Used</option>
                        <option value="DAMAGED">Damaged</option>
                      </select>
                      <input
                        placeholder="Age rating"
                        value={intakeForm[item.id]?.age_rating || ""}
                        onChange={(e) =>
                          setIntakeForm({
                            ...intakeForm,
                            [item.id]: {
                              condition: intakeForm[item.id]?.condition || "LIGHTLY_USED",
                              age_rating: e.target.value,
                            },
                          })
                        }
                        className="w-24 rounded border px-2 py-1 text-xs"
                      />
                      <button
                        onClick={() => completeIntake(donation.id, item.id)}
                        className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
                      >
                        Complete intake
                      </button>
                    </div>
                  )}
                  {item.toy && <p className="mt-1 text-xs text-green-600">Added to inventory</p>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
