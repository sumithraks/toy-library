"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { MembershipTier, Paginated } from "@/lib/types";

export default function SignupPage() {
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    tier_code: "",
  });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  const { data: tiers } = useQuery({
    queryKey: ["membership-tiers"],
    queryFn: () => apiFetch<Paginated<MembershipTier>>("/memberships/tiers/", { auth: false }),
  });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.tier_code) {
      setError("Please select a membership tier");
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch("/auth/signup/", { method: "POST", body: form, auth: false });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Signup failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm rounded-lg border bg-white p-6 text-center shadow-sm">
          <h1 className="mb-2 text-lg font-semibold text-blue-600">Check your email</h1>
          <p className="text-sm text-gray-600">
            We sent a verification link to {form.email}. Your membership application is now
            awaiting staff approval — you can log in any time to check its status.
          </p>
          <button
            onClick={() => router.push("/login")}
            className="mt-4 w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Go to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-lg rounded-lg border bg-white p-6 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-blue-600">Create your account</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700">First name</label>
              <input
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Last name</label>
              <input
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Membership tier</label>
            <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {tiers?.results.map((tier) => (
                <label
                  key={tier.id}
                  className={`cursor-pointer rounded-lg border p-3 text-sm transition ${
                    form.tier_code === tier.code
                      ? "border-blue-600 ring-1 ring-blue-600"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="tier_code"
                    value={tier.code}
                    checked={form.tier_code === tier.code}
                    onChange={(e) => setForm({ ...form, tier_code: e.target.value })}
                    className="sr-only"
                  />
                  <p className="font-semibold">{tier.name}</p>
                  {tier.description && (
                    <p className="mt-1 text-xs text-gray-500">{tier.description}</p>
                  )}
                  <p className="mt-2 text-xs text-gray-500">Joining fee: ${tier.joining_fee}</p>
                  <p className="text-xs text-gray-500">Deposit: ${tier.deposit_amount}</p>
                  <p className="text-xs text-gray-500">
                    {tier.max_concurrent_checkouts} toy(s), {tier.loan_period_days}-day loans
                  </p>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Sign up"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link href="/login" className="text-blue-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
