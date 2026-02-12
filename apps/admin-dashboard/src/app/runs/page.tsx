"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const CP_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_CP_BASE) ||
  "http://localhost:8000";

type RunItem = {
  id: string;
  tenant_id: string;
  pipeline_version_id: string;
  status: string;
  trigger_type: string;
  parameters: Record<string, unknown>;
  claimed_by: string | null;
  claimed_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  heartbeat_at: string | null;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type RunsResponse = {
  items: RunItem[];
  limit: number;
  offset: number;
  count: number;
};

function shortId(id: string, len = 8): string {
  return id.length > len ? `${id.slice(0, len)}…` : id;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusBadgeClass(status: string): string {
  const base = "inline-flex px-2 py-0.5 text-xs font-medium rounded";
  switch (status) {
    case "QUEUED":
      return `${base} bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200`;
    case "RUNNING":
      return `${base} bg-blue-200 text-blue-800 dark:bg-blue-900 dark:text-blue-200`;
    case "SUCCEEDED":
      return `${base} bg-green-200 text-green-800 dark:bg-green-900 dark:text-green-200`;
    case "FAILED":
      return `${base} bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200`;
    default:
      return `${base} bg-gray-100 text-gray-700`;
  }
}

const STATUS_OPTIONS = [
  { value: "", label: "All" },
  { value: "QUEUED", label: "QUEUED" },
  { value: "RUNNING", label: "RUNNING" },
  { value: "SUCCEEDED", label: "SUCCEEDED" },
  { value: "FAILED", label: "FAILED" },
];

export default function RunsPage() {
  const [data, setData] = useState<RunsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const fetchRuns = () => {
    const params = new URLSearchParams({ limit: "20", offset: "0" });
    if (statusFilter) params.set("status", statusFilter);
    const url = `${CP_BASE}/api/runs?${params.toString()}`;
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json: RunsResponse) => {
        setData(json);
        setError(null);
      })
      .catch((err) => setError(err.message ?? "Failed to fetch runs"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 2000);
    return () => clearInterval(interval);
  }, [statusFilter]);

  return (
    <main className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Runs</h1>

      {error && (
        <div
          className="mb-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 rounded text-sm"
          role="alert"
        >
          {error} — retrying on next poll.
        </div>
      )}

      <div className="mb-4 flex items-center gap-4">
        <label className="text-sm font-medium">Status:</label>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 text-sm"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {loading && !data ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="px-4 py-2 font-medium">Created</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Run ID</th>
                <th className="px-4 py-2 font-medium">Claimed by</th>
                <th className="px-4 py-2 font-medium">Pipeline version</th>
                <th className="px-4 py-2 font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {data?.items?.length ? (
                data.items.map((run) => (
                  <tr
                    key={run.id}
                    className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/30"
                  >
                    <td className="px-4 py-2">
                      {formatDate(run.created_at ?? run.started_at)}
                    </td>
                    <td className="px-4 py-2">
                      <span className={statusBadgeClass(run.status)}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono">
                      <Link
                        href={`/runs/${run.id}`}
                        className="text-blue-600 dark:text-blue-400 hover:underline"
                        title={run.id}
                      >
                        {shortId(run.id)}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      {run.claimed_by ?? "—"}
                    </td>
                    <td className="px-4 py-2 font-mono" title={run.pipeline_version_id}>
                      {shortId(run.pipeline_version_id)}
                    </td>
                    <td className="px-4 py-2 text-red-600 dark:text-red-400 max-w-xs truncate" title={run.error_message ?? undefined}>
                      {run.status === "FAILED" && run.error_message
                        ? run.error_message
                        : "—"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-gray-500 text-center">
                    No runs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {data && (
        <p className="mt-2 text-xs text-gray-500">
          Showing {data.count} runs (limit {data.limit}, offset {data.offset})
        </p>
      )}
    </main>
  );
}
