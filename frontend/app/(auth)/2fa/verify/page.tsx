"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, ApiError, setToken } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";

function TwoFactorVerifyInner() {
  const searchParams = useSearchParams();
  const preAuthToken = searchParams.get("pre_auth_token") || "";
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const { refresh } = useAuth();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await apiFetch<{ token: string }>("/auth/2fa/verify/", {
        method: "POST",
        body: { pre_auth_token: preAuthToken, code },
        auth: false,
      });
      setToken(res.token);
      await refresh();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invalid code");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg border bg-white p-6 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-blue-600">Two-factor verification</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Authenticator code or recovery code
            </label>
            <input
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Verifying…" : "Verify"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function TwoFactorVerifyPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading…</div>}>
      <TwoFactorVerifyInner />
    </Suspense>
  );
}
