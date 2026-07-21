"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { CheckoutRecord, Membership, Paginated, Reservation } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { AdminDashboard } from "@/components/admin-dashboard";

export default function DashboardPage() {
  const { user } = useAuth();
  const isStaffOrAdmin = user?.role === "STAFF" || user?.role === "ADMIN";

  const { data: membership } = useQuery({
    queryKey: ["my-membership"],
    queryFn: () => apiFetch<Membership>("/memberships/me/").catch(() => null),
    enabled: !!user && !isStaffOrAdmin,
  });

  const { data: checkouts } = useQuery({
    queryKey: ["my-checkouts"],
    queryFn: () => apiFetch<Paginated<CheckoutRecord>>(`/checkouts/?member=${user?.id}&status=ACTIVE`),
    enabled: !!user && !isStaffOrAdmin,
  });

  const { data: overdueCheckouts } = useQuery({
    queryKey: ["my-checkouts-overdue"],
    queryFn: () => apiFetch<Paginated<CheckoutRecord>>(`/checkouts/?member=${user?.id}&status=OVERDUE`),
    enabled: !!user && !isStaffOrAdmin,
  });

  const { data: reservations } = useQuery({
    queryKey: ["my-reservations"],
    queryFn: () => apiFetch<Paginated<Reservation>>("/reservations/?status=ACTIVE"),
    enabled: !!user && !isStaffOrAdmin,
  });

  if (isStaffOrAdmin) return <AdminDashboard />;

  const active = [...(checkouts?.results ?? []), ...(overdueCheckouts?.results ?? [])];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Welcome, {user?.first_name || user?.email}</h1>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-medium text-gray-700">Membership</h2>
        {membership ? (
          <div className="text-sm text-gray-600">
            <p>
              Tier: <span className="font-medium">{membership.tier.name}</span> — Status:{" "}
              <span className="font-medium">{membership.status}</span>
            </p>
            {membership.renewed_through && <p>Renews through {membership.renewed_through}</p>}
          </div>
        ) : (
          <p className="text-sm text-gray-600">
            You don&apos;t have a membership yet.{" "}
            <Link href="/membership" className="text-blue-600 hover:underline">
              Join now
            </Link>
          </p>
        )}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-medium text-gray-700">Active checkouts</h2>
        {active.length === 0 ? (
          <p className="text-sm text-gray-500">No toys checked out right now.</p>
        ) : (
          <ul className="divide-y">
            {active.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  Due {c.current_due_date}{" "}
                  {c.status === "OVERDUE" && <span className="ml-2 text-red-600">Overdue</span>}
                </span>
                <Link href={`/checkouts?highlight=${c.id}`} className="text-blue-600 hover:underline">
                  Manage
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-medium text-gray-700">Active reservations</h2>
        {reservations?.results.length ? (
          <ul className="divide-y">
            {reservations.results.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                <span>Pick up by {new Date(r.pickup_deadline).toLocaleString()}</span>
                <Link href="/reservations" className="text-blue-600 hover:underline">
                  Manage
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No active reservations.</p>
        )}
      </section>
    </div>
  );
}
