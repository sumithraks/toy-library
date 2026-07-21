"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api-client";

function VerifyEmailInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"pending" | "success" | "error">("pending");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setError("Missing verification token");
      return;
    }
    apiFetch("/auth/verify-email/", { method: "POST", body: { token }, auth: false })
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setError(err instanceof ApiError ? err.message : "Verification failed");
      });
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-lg border bg-white p-6 text-center shadow-sm">
        {status === "pending" && <p className="text-gray-600">Verifying your email…</p>}
        {status === "success" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-green-600">Email verified!</h1>
            <Link href="/login" className="text-blue-600 hover:underline">
              Go to login
            </Link>
          </>
        )}
        {status === "error" && <p className="text-red-600">{error}</p>}
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading…</div>}>
      <VerifyEmailInner />
    </Suspense>
  );
}
