import time
import httpx
import os
import socket

CP_BASE = os.getenv("CP_BASE", "http://localhost:8000").rstrip("/")
WORKER_ID = os.getenv("WORKER_ID", f"{socket.gethostname()}:{os.getpid()}")
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "1.5"))
TENANT_ID = os.getenv("TENANT_ID")


def append_log(
    client: httpx.Client,
    run_id: str,
    message: str,
    level: str = "INFO",
    source: str | None = "worker",
    meta: dict | None = None,
) -> None:
    """Append a log line to the control plane. Best-effort; does not raise."""
    try:
        payload = {"level": level, "message": message}
        if source is not None:
            payload["source"] = source
        if meta is not None:
            payload["meta"] = meta
        r = client.post(f"{CP_BASE}/api/runs/{run_id}/logs", json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"[worker] append_log failed: {e}")


def claim_run(client: httpx.Client):
    payload = {"worker_id": WORKER_ID}
    if TENANT_ID:
        payload["tenant_id"] = TENANT_ID

    r = client.post(f"{CP_BASE}/api/runs/claim", json=payload)
    r.raise_for_status()
    return r.json()


def complete_run(client: httpx.Client, run_id: str, status: str, error_message: str | None = None):
    payload = {"status": status, "error_message": error_message}
    r = client.post(f"{CP_BASE}/api/runs/{run_id}/complete", json=payload)
    r.raise_for_status()
    return r.json()


def main():
    with httpx.Client(timeout=10) as client:
        while True:
            claim = claim_run(client)
            if not claim.get("claimed"):
                print("No queued runs. Sleeping...")
                time.sleep(POLL_SECONDS)
                continue

            run = claim["run"]
            pipeline_version = claim["pipeline_version"]
            run_id = run["id"]
            append_log(client, run_id, f"Claimed run {run_id}", source="worker", meta={"run_id": run_id})
            print(f"Claimed run {run_id} -> RUNNING")

            try:
                dag_spec = pipeline_version.get("dag_spec")
                if dag_spec is None:
                    raise ValueError("pipeline_version.dag_spec is required")

                append_log(client, run_id, "Run began executing", source="worker", meta={"step": "execute"})
                append_log(client, run_id, "Simulate work started", source="worker", meta={"step": "simulate"})

                # Placeholder for DAG execution.
                time.sleep(0.5)

                append_log(client, run_id, "Simulate work finished", source="worker", meta={"step": "simulate"})
                out = complete_run(client, run_id, "SUCCEEDED")
                append_log(client, run_id, "Run completed successfully", source="worker", meta={"status": "SUCCEEDED"})
                print(f"Completed run {run_id} -> {out['run']['status']}")
            except Exception as e:
                append_log(
                    client,
                    run_id,
                    f"Run failed: {e}",
                    level="ERROR",
                    source="worker",
                    meta={"error": str(e), "status": "FAILED"},
                )
                out = complete_run(client, run_id, "FAILED", error_message=str(e))
                print(f"Run {run_id} failed -> {out['run']['status']} ({e})")


if __name__ == "__main__":
    main()
