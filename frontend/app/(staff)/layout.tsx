"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Nav } from "@/components/nav";

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  const isStaffOrAdmin = user?.role === "STAFF" || user?.role === "ADMIN";

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (!isStaffOrAdmin) router.replace("/dashboard");
  }, [loading, user, isStaffOrAdmin, router]);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading…</div>;
  if (!user || !isStaffOrAdmin) return null;

  return (
    <div className="flex min-h-screen flex-col">
      <Nav />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
