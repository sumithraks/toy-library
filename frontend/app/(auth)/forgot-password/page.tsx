"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api-client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiFetch("/auth/password-reset/request/", { method: "POST", body: { email }, auth: false });
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg border bg-white p-6 shadow-sm">
        <h1 className="mb-6 text-xl font-semibold text-blue-600">Forgot password</h1>
        {submitted ? (
          <p className="text-sm text-gray-600">
            If an account exists for that email, we&apos;ve sent a link to reset your password.
          </p>
        ) : (
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
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Sending…" : "Send reset link"}
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
