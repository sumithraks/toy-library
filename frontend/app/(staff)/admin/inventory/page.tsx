"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { CheckoutRecord, Paginated, Toy, ToyGroup } from "@/lib/types";

const STATUSES = [
  "INTAKE",
  "AVAILABLE",
  "RESERVED",
  "CHECKED_OUT",
  "OVERDUE",
  "BROKEN",
  "UNDER_REPAIR",
  "RETIRED",
];

const CHECKOUT_ELIGIBLE_STATUSES = new Set(["AVAILABLE", "RESERVED"]);
const RETURN_ELIGIBLE_STATUSES = new Set(["CHECKED_OUT", "OVERDUE"]);

function groupsInvalidateKeys(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["admin-toy-groups"] });
  queryClient.invalidateQueries({ queryKey: ["admin-toy-group-detail"] });
}

function GroupRows({
  make,
  model_name,
  onTransition,
  onReturn,
}: {
  make: string;
  model_name: string;
  onTransition: (toyId: string, newStatus: string) => Promise<void>;
  onReturn: (toy: Toy, condition: string) => Promise<void>;
}) {
  const [page, setPage] = useState<number | null>(null);
  const [returning, setReturning] = useState<Record<string, { condition: string }>>({});

  const { data } = useQuery({
    queryKey: ["admin-toy-group-detail", make, model_name, page],
    queryFn: () => {
      const params = new URLSearchParams({ make, model_name });
      if (page) params.set("page", String(page));
      return apiFetch<Paginated<Toy>>(`/toys/?${params.toString()}`);
    },
  });

  // make/model_name filters are icontains on the backend, so defensively drop any
  // substring-collision rows (e.g. group "Blocks" vs. a toy named "Wooden Blocks Deluxe").
  const rows = data?.results.filter((t) => t.make === make && t.model_name === model_name) ?? [];

  const pageFromUrl = (url: string | null) => {
    if (!url) return null;
    return Number(new URL(url).searchParams.get("page")) || 1;
  };

  return (
    <>
      {rows.map((toy) => (
        <tr key={toy.id} className="border-t bg-gray-50 text-xs">
          <td className="p-2 pl-8 font-mono" title={toy.id}>
            {toy.id.slice(0, 8)}…
          </td>
          <td className="p-2">{toy.status}</td>
          <td className="p-2">{toy.condition}</td>
          <td className="p-2">
            {CHECKOUT_ELIGIBLE_STATUSES.has(toy.status) ? (
              <Link
                href={`/admin/checkouts?toy=${toy.id}`}
                className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700"
              >
                Check out
              </Link>
            ) : RETURN_ELIGIBLE_STATUSES.has(toy.status) ? (
              <div className="flex items-center gap-1">
                <select
                  value={returning[toy.id]?.condition || "LIGHTLY_USED"}
                  onChange={(e) => setReturning({ ...returning, [toy.id]: { condition: e.target.value } })}
                  className="rounded border px-1 py-1 text-xs"
                >
                  <option value="NEW">New</option>
                  <option value="LIGHTLY_USED">Lightly used</option>
                  <option value="USED">Used</option>
                  <option value="DAMAGED">Damaged</option>
                </select>
                <button
                  onClick={() => onReturn(toy, returning[toy.id]?.condition || "LIGHTLY_USED")}
                  className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                >
                  Return
                </button>
              </div>
            ) : (
              <button
                disabled
                className="cursor-not-allowed rounded bg-gray-300 px-2 py-1 text-xs font-medium text-gray-500"
              >
                Check out
              </button>
            )}
          </td>
          <td className="p-2">
            <select
              value=""
              onChange={(e) => e.target.value && onTransition(toy.id, e.target.value)}
              className="rounded border px-2 py-1 text-xs"
            >
              <option value="">Transition…</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </td>
        </tr>
      ))}
      {(data?.previous || data?.next) && (
        <tr className="border-t bg-gray-50 text-xs">
          <td colSpan={5} className="p-2 pl-8">
            <button
              disabled={!data?.previous}
              onClick={() => setPage(pageFromUrl(data?.previous ?? null))}
              className="mr-2 rounded border px-2 py-1 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              disabled={!data?.next}
              onClick={() => setPage(pageFromUrl(data?.next ?? null))}
              className="rounded border px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AdminInventoryPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ model_name: "", make: "", age: "", status: "" });
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    model_name: "",
    make: "",
    min_age_years: "",
    description: "",
    condition: "NEW",
  });

  const { data: groups } = useQuery({
    queryKey: ["admin-toy-groups", filters],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filters.model_name) params.set("model_name", filters.model_name);
      if (filters.make) params.set("make", filters.make);
      if (filters.age) params.set("age", filters.age);
      if (filters.status) params.set("status", filters.status);
      return apiFetch<ToyGroup[]>(`/toys/groups/?${params.toString()}`);
    },
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["admin-toy-groups"] });

  const createToy = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await apiFetch("/toys/intake/", {
        method: "POST",
        body: { ...form, min_age_years: form.min_age_years ? Number(form.min_age_years) : null },
      });
      setForm({ model_name: "", make: "", min_age_years: "", description: "", condition: "NEW" });
      setShowForm(false);
      invalidate();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add toy to inventory");
    }
  };

  const transition = async (toyId: string, newStatus: string) => {
    setError("");
    try {
      await apiFetch(`/toys/${toyId}/transition/`, {
        method: "POST",
        body: { new_status: newStatus, reason: `Manually set to ${newStatus}` },
      });
      groupsInvalidateKeys(queryClient);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Transition not allowed");
    }
  };

  const returnToy = async (toy: Toy, condition: string) => {
    setError("");
    try {
      const status = toy.status === "OVERDUE" ? "OVERDUE" : "ACTIVE";
      const checkouts = await apiFetch<Paginated<CheckoutRecord>>(
        `/checkouts/?toy=${toy.id}&status=${status}`
      );
      const record = checkouts.results[0];
      if (!record) throw new Error("No active checkout found for this toy");
      await apiFetch(`/checkouts/${record.id}/return/`, {
        method: "POST",
        body: {
          condition,
          damaged_status: condition === "DAMAGED" ? "UNDER_REPAIR" : undefined,
        },
      });
      groupsInvalidateKeys(queryClient);
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Could not return toy");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Inventory</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showForm ? "Cancel" : "Add toy"}
        </button>
      </div>

      {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}

      {showForm && (
        <form onSubmit={createToy} className="grid grid-cols-2 gap-3 rounded-lg border bg-white p-4">
          <input
            placeholder="Model name"
            required
            value={form.model_name}
            onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            className="rounded border px-3 py-2 text-sm"
          />
          <input
            placeholder="Make"
            required
            value={form.make}
            onChange={(e) => setForm({ ...form, make: e.target.value })}
            className="rounded border px-3 py-2 text-sm"
          />
          <input
            placeholder="Min age (years)"
            type="number"
            value={form.min_age_years}
            onChange={(e) => setForm({ ...form, min_age_years: e.target.value })}
            className="rounded border px-3 py-2 text-sm"
          />
          <input
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="col-span-2 rounded border px-3 py-2 text-sm"
          />
          <select
            value={form.condition}
            onChange={(e) => setForm({ ...form, condition: e.target.value })}
            className="col-span-2 rounded border px-3 py-2 text-sm"
          >
            <option value="NEW">New</option>
            <option value="LIGHTLY_USED">Lightly used</option>
            <option value="USED">Used</option>
            <option value="DAMAGED">Damaged</option>
          </select>
          <button
            type="submit"
            className="col-span-2 rounded bg-blue-600 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Add to inventory
          </button>
        </form>
      )}

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
        <select
          value={filters.status}
          onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="rounded border px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-500">
            <tr>
              <th className="p-2">Model / Make</th>
              <th className="p-2">Available / Total</th>
              <th className="p-2">Min age</th>
              <th className="p-2" />
              <th className="p-2" />
            </tr>
          </thead>
          <tbody>
            {groups?.map((g) => {
              const key = `${g.make}::${g.model_name}`;
              const isOpen = !!expanded[key];
              return (
                <Fragment key={key}>
                  <tr
                    className="cursor-pointer border-t hover:bg-gray-50"
                    onClick={() => setExpanded((e) => ({ ...e, [key]: !e[key] }))}
                  >
                    <td className="p-2">
                      {isOpen ? "▾" : "▸"} {g.model_name}{" "}
                      <span className="text-gray-500">— {g.make}</span>
                    </td>
                    <td className="p-2">
                      {g.available_count} / {g.total_count}
                    </td>
                    <td className="p-2">{g.min_age_years != null ? `${g.min_age_years}+` : "—"}</td>
                    <td className="p-2" />
                    <td className="p-2" />
                  </tr>
                  {isOpen && (
                    <GroupRows
                      make={g.make}
                      model_name={g.model_name}
                      onTransition={transition}
                      onReturn={returnToy}
                    />
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
