"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";

function InventoryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7.5 12 3l9 4.5M3 7.5v9L12 21m-9-4.5L12 21m9-4.5V7.5M21 16.5 12 21" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 7.5 12 12m0 0 9-4.5M12 12v9" />
    </svg>
  );
}

function DonationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v13M12 8c-1.5-3-6-3-6 0s4.5 3 6 0Zm0 0c1.5-3 6-3 6 0s-4.5 3-6 0ZM4 12h16v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3Z" />
    </svg>
  );
}

function CheckoutsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2m-6 8 2 2 4-4" />
    </svg>
  );
}

function ReservationsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3.75 8.25h16.5M4.5 6h15a.75.75 0 0 1 .75.75V19.5a.75.75 0 0 1-.75.75h-15a.75.75 0 0 1-.75-.75V6.75A.75.75 0 0 1 4.5 6Z" />
    </svg>
  );
}

function BillingIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m3-9.5c0-1.1-1.34-2-3-2s-3 .9-3 2 1.34 2 3 2 3 .9 3 2-1.34 2-3 2-3-.9-3-2" />
    </svg>
  );
}

function MembersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.7M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
    </svg>
  );
}

function StaffConsoleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="h-6 w-6">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  );
}

type Tile = {
  href: string;
  label: string;
  description: string;
  icon: ReactNode;
  adminOnly?: boolean;
};

const tiles: Tile[] = [
  {
    href: "/admin/inventory",
    label: "Inventory",
    description: "Manage toys and status transitions",
    icon: <InventoryIcon />,
  },
  {
    href: "/admin/donations",
    label: "Accept Donations",
    description: "Review and process incoming donations",
    icon: <DonationIcon />,
  },
  {
    href: "/admin/checkouts",
    label: "Checkouts",
    description: "Track active and overdue checkouts",
    icon: <CheckoutsIcon />,
  },
  {
    href: "/admin/reservations",
    label: "Reservations",
    description: "Manage waitlist and pickup reservations",
    icon: <ReservationsIcon />,
  },
  {
    href: "/admin/billing",
    label: "Billing",
    description: "Ledger entries and payment collection",
    icon: <BillingIcon />,
  },
  {
    href: "/admin/members",
    label: "User Management",
    description: "Manage member accounts and memberships",
    icon: <MembersIcon />,
  },
  {
    href: "/admin/staff",
    label: "Staff Console",
    description: "Manage staff accounts",
    icon: <StaffConsoleIcon />,
    adminOnly: true,
  },
];

export function AdminDashboard() {
  const { user } = useAuth();
  const visibleTiles = tiles.filter((tile) => !tile.adminOnly || user?.role === "ADMIN");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Welcome, {user?.first_name || user?.email}</h1>
      <p className="text-sm text-gray-500">Staff console — jump to an admin area below.</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visibleTiles.map((tile) => (
          <Link
            key={tile.href}
            href={tile.href}
            className="flex items-start gap-3 rounded-lg border bg-white p-4 transition hover:border-blue-300 hover:shadow-sm"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-600">
              {tile.icon}
            </span>
            <span>
              <span className="block font-medium text-gray-800">{tile.label}</span>
              <span className="block text-sm text-gray-500">{tile.description}</span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
