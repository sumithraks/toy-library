"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError, setToken } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";

function LoginInner() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const { refresh } = useAuth();
  const resetSuccess = searchParams.get("reset") === "success";

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await apiFetch<{ token?: string; pre_auth_token?: string; requires_2fa: boolean }>(
        "/auth/login/",
        { method: "POST", body: { email, password }, auth: false }
      );
      if (res.requires_2fa && res.pre_auth_token) {
        router.push(`/2fa/verify?pre_auth_token=${res.pre_auth_token}`);
        return;
      }
      if (res.token) {
        setToken(res.token);
        await refresh();
        router.push("/dashboard");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg border bg-white p-6 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-blue-600">Toy Library — Log in</h1>
        {resetSuccess && (
          <p className="mb-4 rounded bg-green-50 p-2 text-sm text-green-700">
            Your password has been reset. Log in with your new password.
          </p>
        )}
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <p className="text-right text-sm">
            <Link href="/forgot-password" className="text-blue-600 hover:underline">
              Forgot password?
            </Link>
          </p>
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          No account?{" "}
          <Link href="/signup" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading…</div>}>
      <LoginInner />
    </Suspense>
  );
}
