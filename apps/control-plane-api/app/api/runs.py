import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import LogAppendIn, RunClaimIn, RunCompleteIn
from app.db.deps import get_db

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _pipeline_run_columns(db: Session) -> set[str]:
    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'pipeline_runs'
            """
        )
    ).fetchall()
    return {row[0] for row in rows}


def _run_returning_sql(columns: set[str]) -> str:
    claimed_at = "claimed_at" if "claimed_at" in columns else "NULL::timestamptz AS claimed_at"
    claimed_by = "claimed_by" if "claimed_by" in columns else "NULL::text AS claimed_by"
    error_message = "error_message" if "error_message" in columns else "NULL::text AS error_message"
    return f"""
        id,
        tenant_id,
        pipeline_version_id,
        status,
        started_at,
        {claimed_at},
        {claimed_by},
        finished_at,
        {error_message}
    """


@router.post("/claim")
def claim_run(body: RunClaimIn, db: Session = Depends(get_db)):
    tenant_filter = ""
    params: dict[str, str] = {"worker_id": body.worker_id}
    if body.tenant_id:
        tenant_filter = "AND r.tenant_id = :tenant_id"
        params["tenant_id"] = body.tenant_id

    with db.begin():
        run_columns = _pipeline_run_columns(db)

        row = db.execute(
            text(
                f"""
                SELECT r.id
                FROM pipeline_runs r
                WHERE r.status = 'QUEUED'
                {tenant_filter}
                ORDER BY r.created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            ),
            params,
        ).mappings().first()

        if row is None:
            return {"claimed": False}

        set_clauses = [
            "status='RUNNING'",
            "started_at=COALESCE(started_at, NOW())",
        ]
        if "claimed_at" in run_columns:
            set_clauses.append("claimed_at=NOW()")
        if "claimed_by" in run_columns:
            set_clauses.append("claimed_by=:worker_id")
        if "heartbeat_at" in run_columns:
            set_clauses.append("heartbeat_at=NOW()")
        if "updated_at" in run_columns:
            set_clauses.append("updated_at=NOW()")

        run = db.execute(
            text(
                f"""
                UPDATE pipeline_runs
                SET {", ".join(set_clauses)}
                WHERE id=:run_id
                RETURNING {_run_returning_sql(run_columns)}
                """
            ),
            {"run_id": row["id"], "worker_id": body.worker_id},
        ).mappings().one()

        pipeline_version = db.execute(
            text(
                """
                SELECT id, status, dag_spec
                FROM pipeline_versions
                WHERE id=:pipeline_version_id
                """
            ),
            {"pipeline_version_id": run["pipeline_version_id"]},
        ).mappings().first()

        if pipeline_version is None:
            raise HTTPException(status_code=409, detail="pipeline version not found for claimed run")

    return {
        "claimed": True,
        "run": dict(run),
        "pipeline_version": dict(pipeline_version),
    }


@router.post("/{run_id}/complete")
def complete_run(run_id: str, body: RunCompleteIn, db: Session = Depends(get_db)):
    with db.begin():
        run_columns = _pipeline_run_columns(db)
        set_clauses = [
            "status=CAST(:status AS VARCHAR)",
            "finished_at=NOW()",
        ]
        if "heartbeat_at" in run_columns:
            set_clauses.append("heartbeat_at=NOW()")
        if "error_message" in run_columns:
            set_clauses.append(
                "error_message=CASE WHEN CAST(:status AS VARCHAR)='FAILED' THEN :error_message ELSE NULL END"
            )
        if "updated_at" in run_columns:
            set_clauses.append("updated_at=NOW()")

        run = db.execute(
            text(
                f"""
                UPDATE pipeline_runs
                SET {", ".join(set_clauses)}
                WHERE id=:run_id AND status='RUNNING'
                RETURNING {_run_returning_sql(run_columns)}
                """
            ),
            {
                "run_id": run_id,
                "status": body.status,
                "error_message": body.error_message,
            },
        ).mappings().first()

        if run is None:
            raise HTTPException(
                status_code=409,
                detail="run not RUNNING or not found",
            )

    return {"ok": True, "run": dict(run)}


@router.get("")
def list_runs(
    tenant_id: str | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if tenant_id is not None:
        where.append("tenant_id = :tenant_id")
        params["tenant_id"] = str(tenant_id)

    if status is not None:
        where.append("status = CAST(:status AS VARCHAR)")
        params["status"] = status

    sql = text(f"""
SELECT id, tenant_id, pipeline_version_id, status, trigger_type, parameters,
       claimed_by, claimed_at, started_at, finished_at, heartbeat_at, error_message,
       created_at, updated_at
FROM pipeline_runs
WHERE {" AND ".join(where)}
ORDER BY created_at DESC
LIMIT :limit OFFSET :offset
""")
    rows = db.execute(sql, params).mappings().all()
    return {"items": [dict(r) for r in rows], "limit": limit, "offset": offset, "count": len(rows)}


@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            """
            SELECT id, tenant_id, pipeline_version_id, status, trigger_type, parameters,
                   claimed_by, claimed_at, started_at, finished_at, heartbeat_at, error_message,
                   created_at, updated_at
            FROM pipeline_runs
            WHERE id = :run_id
            """
        ),
        {"run_id": run_id},
    ).mappings().first()
    if row is None:
        return JSONResponse(
            status_code=404,
            content={"found": False, "reason": "run_not_found"},
        )
    return {"found": True, "run": dict(row)}


def _run_exists(db: Session, run_id: str) -> dict | None:
    row = db.execute(
        text("SELECT id, tenant_id FROM pipeline_runs WHERE id = :run_id"),
        {"run_id": run_id},
    ).mappings().first()
    return dict(row) if row else None


@router.post("/{run_id}/logs")
def append_run_log(run_id: str, body: LogAppendIn, db: Session = Depends(get_db)):
    run = _run_exists(db, run_id)
    if run is None:
        return JSONResponse(
            status_code=404,
            content={"found": False, "reason": "run_not_found"},
        )
    meta_json = json.dumps(body.meta) if body.meta is not None else None
    row = db.execute(
        text(
            """
            INSERT INTO pipeline_run_logs (id, run_id, tenant_id, level, message, source, meta)
            VALUES (gen_random_uuid()::text, :run_id, :tenant_id, :level, :message, :source, CAST(:meta AS jsonb))
            RETURNING id, ts, level, message, source, meta
            """
        ),
        {
            "run_id": run_id,
            "tenant_id": run["tenant_id"],
            "level": body.level,
            "message": body.message,
            "source": body.source,
            "meta": meta_json,
        },
    ).mappings().one()
    db.commit()
    out = dict(row)
    if out.get("ts"):
        out["ts"] = out["ts"].isoformat()
    return {"ok": True, "log": out}


@router.get("/{run_id}/logs")
def get_run_logs(
    run_id: str,
    limit: int = Query(200, ge=1, le=1000),
    before_ts: str | None = Query(None, description="ISO timestamp for pagination backwards"),
    after_ts: str | None = Query(None, description="ISO timestamp for tailing"),
    order: str = Query("asc", description="asc or desc"),
    db: Session = Depends(get_db),
):
    run = _run_exists(db, run_id)
    if run is None:
        return JSONResponse(
            status_code=404,
            content={"found": False, "run_id": run_id, "logs": []},
        )
    order_dir = "DESC" if order.lower() == "desc" else "ASC"
    params: dict = {"run_id": run_id, "limit": limit}
    conditions = ["run_id = :run_id"]
    if before_ts:
        conditions.append("ts < CAST(:before_ts AS timestamptz)")
        params["before_ts"] = before_ts
    if after_ts:
        conditions.append("ts > CAST(:after_ts AS timestamptz)")
        params["after_ts"] = after_ts
    sql = text(
        f"""
        SELECT id, ts, level, message, source, meta
        FROM pipeline_run_logs
        WHERE {" AND ".join(conditions)}
        ORDER BY ts {order_dir}
        LIMIT :limit
        """
    )
    rows = db.execute(sql, params).mappings().all()
    logs = []
    for r in rows:
        row_dict = dict(r)
        if row_dict.get("ts"):
            row_dict["ts"] = row_dict["ts"].isoformat()
        logs.append(row_dict)
    return {"found": True, "run_id": run_id, "logs": logs}
