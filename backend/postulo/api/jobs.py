"""Background jobs: start the demo job, read a job, follow it live (SSE)."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from postulo.services.demo import DEMO_JOB_TYPE, DEMO_STEPS, make_demo_job
from postulo.services.jobs import JobManager, JobRead

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

HEARTBEAT_SECONDS = 15.0


def _manager(request: Request) -> JobManager:
    manager: JobManager = request.app.state.jobs
    return manager


@router.post("/demo", status_code=status.HTTP_202_ACCEPTED)
async def start_demo_job(request: Request) -> JobRead:
    step_seconds: float = request.app.state.demo_step_seconds
    return _manager(request).start(DEMO_JOB_TYPE, DEMO_STEPS, make_demo_job(step_seconds))


@router.get("/{job_id}")
def get_job(job_id: str, request: Request) -> JobRead:
    job = _manager(request).get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable.")
    return job


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


async def _event_stream(manager: JobManager, job_id: str) -> AsyncIterator[str]:
    """`progress` events, then a final `end` event. Comments keep the connection alive."""
    updates = manager.subscribe(job_id)
    try:
        next_update = asyncio.ensure_future(anext(updates))
        while True:
            done, _ = await asyncio.wait({next_update}, timeout=HEARTBEAT_SECONDS)
            if not done:
                yield ": keep-alive\n\n"
                continue
            try:
                snapshot = next_update.result()
            except StopAsyncIteration:
                return
            payload = snapshot.model_dump_json()
            if snapshot.status.is_final:
                yield _sse("end", payload)
                return
            yield _sse("progress", payload)
            next_update = asyncio.ensure_future(anext(updates))
    finally:
        with contextlib.suppress(Exception):
            next_update.cancel()
        await updates.aclose()


@router.get("/{job_id}/events")
def follow_job(job_id: str, request: Request) -> StreamingResponse:
    manager = _manager(request)
    if manager.get(job_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tâche introuvable.")
    return StreamingResponse(
        _event_stream(manager, job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
