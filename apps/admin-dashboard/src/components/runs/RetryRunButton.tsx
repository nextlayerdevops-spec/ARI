"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";

const CP_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_CP_BASE) ||
  "http://localhost:8000";

type RetryResponse = {
  ok: boolean;
  run?: { id: string };
  retry_of?: string;
};

function parseParametersJson(
  value: string
): { ok: true; data: Record<string, unknown> } | { ok: false; error: string } {
  const trimmed = value.trim();
  if (trimmed === "") return { ok: true, data: {} };
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
      return {
        ok: false,
        error: "Parameters must be a JSON object (e.g. {} or {\"key\": \"value\"}).",
      };
    }
    return { ok: true, data: parsed as Record<string, unknown> };
  } catch {
    return {
      ok: false,
      error: "Invalid JSON. Parameters must be a valid JSON object.",
    };
  }
}

type RetryRunButtonProps = {
  runId: string;
  disabled?: boolean;
  defaultParameters?: Record<string, unknown> | null;
  onRetried?: (newRunId: string) => void;
  className?: string;
  label?: string;
};

export function RetryRunButton({
  runId,
  disabled = false,
  defaultParameters = {},
  onRetried,
  className = "px-3 py-1.5 text-sm font-medium rounded bg-blue-200 text-blue-800 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-300 dark:hover:bg-blue-800",
  label = "Retry",
}: RetryRunButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [parametersText, setParametersText] = useState("{}");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const initialJson =
    defaultParameters != null && typeof defaultParameters === "object"
      ? JSON.stringify(defaultParameters, null, 2)
      : "{}";

  const handleOpen = useCallback(() => {
    setParametersText(initialJson);
    setSubmitError(null);
    setOpen(true);
  }, [initialJson]);

  useEffect(() => {
    if (open) setParametersText(initialJson);
  }, [open, initialJson]);

  const handleClose = useCallback(() => {
    if (!submitting) {
      setOpen(false);
      setSubmitError(null);
    }
  }, [submitting]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const parsed = parseParametersJson(parametersText);
      if (!parsed.ok) {
        setSubmitError(parsed.error);
        return;
      }
      setSubmitError(null);
      setSubmitting(true);
      try {
        const res = await fetch(`${CP_BASE}/api/runs/${runId}/retry`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ parameters: parsed.data }),
        });
        const json: RetryResponse & { reason?: string; detail?: string } =
          await res.json().catch(() => ({}));
        if (!res.ok) {
          const reason = json.reason ?? (typeof json.detail === "string" ? json.detail : undefined);
          if (res.status === 409) {
            if (reason === "invalid_state")
              setSubmitError("Run is not retryable (wrong status).");
            else if (reason === "pipeline_version_not_approved")
              setSubmitError("Pipeline version is not approved.");
            else setSubmitError(reason ?? "Run is not retryable.");
          } else {
            setSubmitError(reason ?? `HTTP ${res.status}`);
          }
          setSubmitting(false);
          return;
        }
        const newRunId = json.run?.id;
        if (newRunId) {
          onRetried?.(newRunId);
          router.push(`/runs/${newRunId}`);
          return;
        }
        setSubmitError("No run id in response");
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Request failed"
        );
      } finally {
        setSubmitting(false);
      }
    },
    [runId, parametersText, router, onRetried]
  );

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        disabled={disabled}
        className={className}
      >
        {label}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={handleClose}
          role="dialog"
          aria-modal="true"
          aria-labelledby="retry-run-title"
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full border border-gray-200 dark:border-gray-700"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="retry-run-title" className="text-lg font-semibold px-4 pt-4">
              Retry run
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 px-4 mt-1">
              Creates a new QUEUED run with the same pipeline version. You can
              override parameters below. You will be redirected to the new run
              page.
            </p>
            <form onSubmit={handleSubmit} className="p-4 space-y-3">
              <label className="block text-sm font-medium">
                Parameters <span className="text-gray-500 font-normal">(JSON object)</span>
              </label>
              <textarea
                value={parametersText}
                onChange={(e) => setParametersText(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 font-mono text-sm"
                placeholder="{}"
                spellCheck={false}
                disabled={submitting}
              />
              {submitError && (
                <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                  {submitError}
                </p>
              )}
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={submitting}
                  className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-3 py-1.5 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "Creating retry…" : "Create retry"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
