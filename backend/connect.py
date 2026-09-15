from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config.settings import Config
from src.application.services.extraction_service import DataMonitoringService
from src.shared.file_handler import FileLoader


app = FastAPI(title="ADA Data Monitoring Refresh API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

JobStatus = Literal["queued", "running", "success", "failed", "cancelled"]
QueryStatus = Literal["pending", "running", "success", "empty", "failed", "cancelled"]


class RefreshRequest(BaseModel):
    client: str = Field(..., min_length=1)
    include_database: bool = True
    include_ui: bool = True


class QueryProgress(BaseModel):
    name: str
    status: QueryStatus = "pending"
    progress: int = 0


class RefreshJob(BaseModel):
    id: str
    client: str
    status: JobStatus
    progress: int = 0
    database_progress: int = 0
    ui_progress: int = 0
    current_step: str = "Queued"
    database_tables: list[QueryProgress] = Field(default_factory=list)
    ui_tables: list[QueryProgress] = Field(default_factory=list)
    include_database: bool
    include_ui: bool
    cancel_requested: bool = False
    message: str
    created_at: str
    updated_at: str


jobs: dict[str, RefreshJob] = {}
jobs_lock = threading.Lock()
run_lock = threading.Lock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_clients() -> list[str]:
    config = Config.from_defaults()
    yaml_config = FileLoader.load_yaml(config.yaml_path)
    return [
        db.get("client")
        for db in yaml_config.get("databases", [])
        if db.get("client")
    ]


def _load_query_progress(folder) -> list[QueryProgress]:
    return [
        QueryProgress(name=name)
        for name, _ in FileLoader.load_all_sql(folder)
    ]


def _set_job(job_id: str, **changes) -> None:
    with jobs_lock:
        jobs[job_id] = jobs[job_id].model_copy(update={**changes, "updated_at": _now()})


def _is_cancel_requested(job_id: str) -> bool:
    with jobs_lock:
        return jobs[job_id].cancel_requested


def _cancel_pending_queries(job: RefreshJob) -> RefreshJob:
    job = job.model_copy(deep=True)

    for query in [*job.database_tables, *job.ui_tables]:
        if query.status in {"pending", "running"}:
            query.status = "cancelled"

    job.updated_at = _now()
    return job


def _mark_cancelled(job_id: str) -> None:
    with jobs_lock:
        job = _cancel_pending_queries(jobs[job_id])
        job.status = "cancelled"
        job.current_step = "Cancelled"
        job.message = f"Refresh cancelled for {job.client}."
        jobs[job_id] = job


def _query_group_progress(queries: list[QueryProgress]) -> int:
    if not queries:
        return 0

    return round(sum(query.progress for query in queries) / len(queries))


def _overall_progress(job: RefreshJob) -> int:
    groups = []

    if job.include_database:
        groups.append(job.database_progress)

    if job.include_ui:
        groups.append(job.ui_progress)

    if not groups:
        return 0

    return round(sum(groups) / len(groups))


def _update_query_progress(job_id: str, group: Literal["database", "ui"], name: str, status: QueryStatus) -> None:
    if _is_cancel_requested(job_id):
        return

    progress = 0
    if status == "running":
        progress = 45
    elif status in {"success", "empty"}:
        progress = 100

    with jobs_lock:
        job = jobs[job_id].model_copy(deep=True)
        queries = job.database_tables if group == "database" else job.ui_tables

        for query in queries:
            if query.name == name:
                query.status = status
                query.progress = progress
                break

        if group == "database":
            job.database_progress = _query_group_progress(queries)
            job.current_step = f"Database: {name}"
        else:
            job.ui_progress = _query_group_progress(queries)
            job.current_step = f"UI: {name}"

        job.progress = _overall_progress(job)
        job.message = f"{name} is {status}."
        job.updated_at = _now()
        jobs[job_id] = job


def _run_refresh(job_id: str) -> None:
    with jobs_lock:
        job = jobs[job_id]

    if not run_lock.acquire(blocking=False):
        _set_job(
            job_id,
            status="failed",
            progress=0,
            database_progress=0,
            ui_progress=0,
            current_step="Blocked",
            message="Another refresh job is already running.",
        )
        return

    try:
        _set_job(
            job_id,
            status="running",
            progress=5,
            database_progress=0,
            ui_progress=0,
            current_step="Starting",
            message=f"Starting refresh for {job.client}...",
        )
        service = DataMonitoringService()

        if job.include_database and job.include_ui:
            if _is_cancel_requested(job_id):
                _mark_cancelled(job_id)
                return

            _set_job(
                job_id,
                progress=10,
                database_progress=15,
                current_step="Database tables",
                message=f"Refreshing DB tables for {job.client}...",
            )
            service.extract_and_push_specific_client(
                job.client,
                progress_callback=lambda name, status: _update_query_progress(job_id, "database", name, status),
            )

            if _is_cancel_requested(job_id):
                _mark_cancelled(job_id)
                return

            _set_job(
                job_id,
                progress=60,
                database_progress=100,
                ui_progress=15,
                current_step="UI metrics",
                message=f"DB refresh done. Refreshing UI metrics for {job.client}...",
            )
            service.extract_and_push_specific_client_ui(
                job.client,
                progress_callback=lambda name, status: _update_query_progress(job_id, "ui", name, status),
            )

        elif job.include_database:
            if _is_cancel_requested(job_id):
                _mark_cancelled(job_id)
                return

            _set_job(
                job_id,
                progress=10,
                database_progress=15,
                current_step="Database tables",
                message=f"Refreshing DB tables for {job.client}...",
            )
            service.extract_and_push_specific_client(
                job.client,
                progress_callback=lambda name, status: _update_query_progress(job_id, "database", name, status),
            )

            if _is_cancel_requested(job_id):
                _mark_cancelled(job_id)
                return

            _set_job(job_id, progress=90, database_progress=100, current_step="Finalizing")

        elif job.include_ui:
            if _is_cancel_requested(job_id):
                _mark_cancelled(job_id)
                return

            _set_job(
                job_id,
                progress=10,
                ui_progress=15,
                current_step="UI metrics",
                message=f"Refreshing UI metrics for {job.client}...",
            )
            service.extract_and_push_specific_client_ui(
                job.client,
                progress_callback=lambda name, status: _update_query_progress(job_id, "ui", name, status),
            )

            if _is_cancel_requested(job_id):
                _mark_cancelled(job_id)
                return

            _set_job(job_id, progress=90, ui_progress=100, current_step="Finalizing")

        _set_job(
            job_id,
            status="success",
            progress=100,
            database_progress=100 if job.include_database else 0,
            ui_progress=100 if job.include_ui else 0,
            current_step="Completed",
            message=f"Refresh completed for {job.client}.",
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            current_step="Failed",
            message=str(exc),
        )
    finally:
        run_lock.release()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/clients")
def list_clients() -> dict[str, list[str]]:
    return {"clients": _load_clients()}


@app.post("/refresh", status_code=202)
def refresh_client(request: RefreshRequest, background_tasks: BackgroundTasks) -> RefreshJob:
    clients = _load_clients()
    client_lookup = {client.lower(): client for client in clients}
    client = client_lookup.get(request.client.lower())

    if not client:
        raise HTTPException(
            status_code=404,
            detail=f"Client '{request.client}' not found. Available clients: {', '.join(clients)}",
        )

    if not request.include_database and not request.include_ui:
        raise HTTPException(status_code=400, detail="Select at least one refresh target.")

    config = Config.from_defaults()
    job = RefreshJob(
        id=uuid.uuid4().hex,
        client=client,
        status="queued",
        progress=0,
        database_progress=0,
        ui_progress=0,
        current_step="Queued",
        database_tables=_load_query_progress(config.sql_folder_path) if request.include_database else [],
        ui_tables=_load_query_progress(config.sql_folder_path_UI) if request.include_ui else [],
        include_database=request.include_database,
        include_ui=request.include_ui,
        cancel_requested=False,
        message=f"Queued refresh for {client}.",
        created_at=_now(),
        updated_at=_now(),
    )

    with jobs_lock:
        jobs[job.id] = job

    background_tasks.add_task(_run_refresh, job.id)
    return job


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> RefreshJob:
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return job


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> RefreshJob:
    with jobs_lock:
        job = jobs.get(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")

        if job.status in {"success", "failed", "cancelled"}:
            return job

        job = _cancel_pending_queries(job)
        job.cancel_requested = True
        job.status = "cancelled" if job.status == "queued" else job.status
        job.current_step = "Cancelling"
        job.message = f"Cancelling refresh for {job.client}..."
        jobs[job_id] = job
        return job
