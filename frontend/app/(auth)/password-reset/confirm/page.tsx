"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api-client";

function PasswordResetConfirmInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!token) {
      setError("Missing reset token");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch("/auth/password-reset/confirm/", {
        method: "POST",
        body: { token, password },
        auth: false,
      });
      router.push("/login?reset=success");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reset password");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg border bg-white p-6 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-blue-600">Reset password</h1>
        {!token ? (
          <p className="text-sm text-red-600">Missing or invalid reset link.</p>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">New password</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Confirm new password</label>
              <input
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Resetting…" : "Reset password"}
            </button>
          </form>
        )}
        <p className="mt-4 text-center text-sm text-gray-600">
          <Link href="/login" className="text-blue-600 hover:underline">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function PasswordResetConfirmPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading…</div>}>
      <PasswordResetConfirmInner />
    </Suspense>
  );
}
