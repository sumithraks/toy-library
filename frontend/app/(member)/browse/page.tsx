"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Paginated, Toy } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  AVAILABLE: "bg-green-100 text-green-800",
  RESERVED: "bg-yellow-100 text-yellow-800",
  CHECKED_OUT: "bg-gray-100 text-gray-700",
  OVERDUE: "bg-red-100 text-red-800",
  INTAKE: "bg-blue-100 text-blue-800",
  BROKEN: "bg-red-100 text-red-800",
  UNDER_REPAIR: "bg-orange-100 text-orange-800",
  RETIRED: "bg-gray-100 text-gray-500",
};

export default function BrowsePage() {
  const [filters, setFilters] = useState({ model_name: "", make: "", age: "" });

  const { data, isLoading } = useQuery({
    queryKey: ["toys", filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.model_name) params.set("model_name", filters.model_name);
      if (filters.make) params.set("make", filters.make);
      if (filters.age) params.set("age", filters.age);
      return apiFetch<Paginated<Toy>>(`/toys/?${params.toString()}`);
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Browse toys</h1>
        <div className="flex flex-wrap gap-2">
          <input
            placeholder="Model…"
            value={filters.model_name}
            onChange={(e) => setFilters({ ...filters, model_name: e.target.value })}
            className="w-40 rounded border px-3 py-2 text-sm"
          />
          <input
            placeholder="Make…"
            value={filters.make}
            onChange={(e) => setFilters({ ...filters, make: e.target.value })}
            className="w-40 rounded border px-3 py-2 text-sm"
          />
          <input
            placeholder="Age"
            type="number"
            min={0}
            value={filters.age}
            onChange={(e) => setFilters({ ...filters, age: e.target.value })}
            className="w-24 rounded border px-3 py-2 text-sm"
          />
        </div>
      </div>

      {isLoading && <p className="text-gray-500">Loading…</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((toy) => (
          <Link
            key={toy.id}
            href={`/browse/${toy.id}`}
            className="rounded-lg border bg-white p-4 hover:shadow-sm"
          >
            <div className="mb-2 flex items-start justify-between">
              <h3 className="font-medium">{toy.model_name}</h3>
              <span className={`rounded px-2 py-0.5 text-xs ${STATUS_COLORS[toy.status]}`}>
                {toy.status.replace("_", " ")}
              </span>
            </div>
            <p className="text-sm text-gray-500">{toy.make}</p>
            {toy.min_age_years != null && (
              <p className="mt-1 text-xs text-gray-400">Age {toy.min_age_years}+</p>
            )}
          </Link>
        ))}
      </div>
      {data && data.results.length === 0 && (
        <p className="text-gray-500">No toys match your filters.</p>
      )}
    </div>
  );
}
