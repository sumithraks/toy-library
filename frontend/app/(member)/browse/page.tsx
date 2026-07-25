"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
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
  const [descriptionQuery, setDescriptionQuery] = useState("");
  const [activeDescriptionQuery, setActiveDescriptionQuery] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["toys", filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.model_name) params.set("model_name", filters.model_name);
      if (filters.make) params.set("make", filters.make);
      if (filters.age) params.set("age", filters.age);
      return apiFetch<Paginated<Toy>>(`/toys/?${params.toString()}`);
    },
    enabled: !activeDescriptionQuery,
  });

  const {
    data: semanticResults,
    isLoading: semanticLoading,
    error: semanticError,
  } = useQuery({
    queryKey: ["toys-semantic-search", activeDescriptionQuery],
    queryFn: () =>
      apiFetch<Toy[]>(`/toys/semantic-search/?q=${encodeURIComponent(activeDescriptionQuery)}`),
    enabled: !!activeDescriptionQuery,
    retry: false,
  });

  const runDescriptionSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveDescriptionQuery(descriptionQuery.trim());
  };

  const clearDescriptionSearch = () => {
    setDescriptionQuery("");
    setActiveDescriptionQuery("");
  };

  const results = activeDescriptionQuery ? semanticResults : data?.results;
  const loading = activeDescriptionQuery ? semanticLoading : isLoading;

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

      <form onSubmit={runDescriptionSearch} className="flex flex-wrap gap-2">
        <input
          placeholder="Describe what you're looking for, e.g. 'wooden toy that helps with counting'"
          value={descriptionQuery}
          onChange={(e) => setDescriptionQuery(e.target.value)}
          className="min-w-[280px] flex-1 rounded border px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!descriptionQuery.trim()}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Search
        </button>
        {activeDescriptionQuery && (
          <button
            type="button"
            onClick={clearDescriptionSearch}
            className="rounded border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Clear
          </button>
        )}
      </form>

      {semanticError && (
        <p className="rounded bg-red-50 p-2 text-sm text-red-700">
          {semanticError instanceof ApiError ? semanticError.message : "Could not run that search"}
        </p>
      )}

      {loading && <p className="text-gray-500">Loading…</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {results?.map((toy) => (
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
      {results && results.length === 0 && (
        <p className="text-gray-500">
          {activeDescriptionQuery ? "No toys matched that description." : "No toys match your filters."}
        </p>
      )}
    </div>
  );
}
