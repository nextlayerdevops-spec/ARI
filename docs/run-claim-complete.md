# Control Plane Run Claim/Complete — Verification

## Prerequisite

Ensure at least one `PipelineRun` has `status = QUEUED`. If none exists, create one:

```powershell
# Create a run (pipeline_version must be APPROVED)
$body = @{ tenant_id = "580115b4-a291-4917-8dbd-247cfa13e2d6"; pipeline_version_id = "b31dbeba-3a2e-4fa9-a084-72c75f9f18a3" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/runs" -ContentType "application/json" -Body $body
```

## 1) Start API and DB

```powershell
# From repo root: start Postgres
docker compose -f infra/docker-compose.yml up -d

cd apps/control-plane-api
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/nextlayer"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## 2) Start worker

```powershell
cd apps/data-plane-worker
$env:CP_BASE = "http://localhost:8000"
$env:POLL_SECONDS = "1.5"
# $env:WORKER_ID = "dpw-1"   # optional; default is hostname:pid
python worker.py
```

Worker will poll `POST /api/runs/claim` every ~1.5s, process claimed runs (0.5s placeholder), then call `POST /api/runs/{run_id}/complete` with SUCCEEDED or FAILED.

## 3) Manual endpoint checks (PowerShell)

**Claim one run**

```powershell
$claimBody = @{ worker_id = "dpw-manual"; tenant_id = "580115b4-a291-4917-8dbd-247cfa13e2d6" } | ConvertTo-Json
$claim = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/runs/claim" -ContentType "application/json" -Body $claimBody
$claim
# If none queued: claimed = false. If claimed: claimed = true, run = {...}, pipeline_version = {...} (includes dag_spec).
```

**Complete a run** (only works when run is RUNNING, e.g. just claimed)

```powershell
$runId = $claim.run.id
$completeBody = @{ status = "SUCCEEDED" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/runs/$runId/complete" -ContentType "application/json" -Body $completeBody
# On wrong state (e.g. not RUNNING): 409 with message "run not RUNNING or not found".
```

**Complete with FAILED**

```powershell
$completeBody = @{ status = "FAILED"; error_message = "Something went wrong" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/runs/$runId/complete" -ContentType "application/json" -Body $completeBody
```

## 4) List runs (GET /api/runs)

```powershell
# Default (limit=20, offset=0)
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/runs"

# With filters: tenant_id, status, limit, offset
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/api/runs?tenant_id=580115b4-a291-4917-8dbd-247cfa13e2d6&status=QUEUED&limit=5&offset=0"
```

## 5) Verify run status (psql)

```powershell
docker exec -it <postgres_container_name> psql -U postgres -d nextlayer -c "SELECT id, status, claimed_by, started_at, finished_at, error_message FROM pipeline_runs ORDER BY created_at DESC LIMIT 5;"
```

Or with a known run id:

```sql
SELECT id, status, claimed_by, started_at, finished_at, error_message FROM pipeline_runs WHERE id = 'f1469c6e-5208-4914-8762-109feb5fb737';
```
