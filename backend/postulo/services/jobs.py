"""Background jobs with live progress (docs/SPEC.md section 2.4).

A job runs as an asyncio task inside the server process. Its state is persisted
in the `job` table after every change, and pushed to subscribers (the SSE
endpoint) through per-subscriber queues.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine
from sqlmodel import Session

from postulo.db.models import Job, JobStatus, StepStatus, utcnow
from postulo.errors import UserError
from postulo.services.llm.base import LLMError

logger = logging.getLogger(__name__)

GENERIC_ERROR = "La tâche a échoué de façon inattendue."


class JobStep(BaseModel):
    key: str
    status: StepStatus


class JobRead(BaseModel):
    """Public view of a job (API and SSE payload)."""

    id: str
    type: str
    status: JobStatus
    progress: int
    steps: list[JobStep]
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_job(cls, job: Job) -> JobRead:
        return cls.model_validate(job, from_attributes=True)


class JobContext:
    """Handle given to a running job function to report progress."""

    def __init__(self, manager: JobManager, job_id: str) -> None:
        self._manager = manager
        self.job_id = job_id

    def start_step(self, key: str) -> None:
        self._manager._update(self.job_id, step=(key, StepStatus.RUNNING))

    def finish_step(self, key: str, progress: int | None = None) -> None:
        self._manager._update(self.job_id, step=(key, StepStatus.DONE), progress=progress)

    def set_progress(self, progress: int) -> None:
        self._manager._update(self.job_id, progress=progress)


JobFunc = Callable[[JobContext], Awaitable[dict[str, Any] | None]]


class JobManager:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._subscribers: dict[str, set[asyncio.Queue[JobRead]]] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    # --- public API ---------------------------------------------------------------

    def start(self, job_type: str, steps: Sequence[str], func: JobFunc) -> JobRead:
        """Persist a new job and run `func` in the background."""
        job = Job(
            type=job_type,
            steps=[{"key": key, "status": StepStatus.PENDING.value} for key in steps],
        )
        with Session(self._engine) as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            snapshot = JobRead.from_job(job)
        task = asyncio.create_task(self._run(snapshot.id, func), name=f"job-{snapshot.id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return snapshot

    def get(self, job_id: str) -> JobRead | None:
        with Session(self._engine) as session:
            job = session.get(Job, job_id)
            return JobRead.from_job(job) if job else None

    async def subscribe(self, job_id: str) -> AsyncGenerator[JobRead]:
        """Yield the current state, then every change, until the job is final."""
        queue: asyncio.Queue[JobRead] = asyncio.Queue()
        self._subscribers.setdefault(job_id, set()).add(queue)
        try:
            current = self.get(job_id)
            if current is None:
                return
            yield current
            if current.status.is_final:
                return
            while True:
                snapshot = await queue.get()
                yield snapshot
                if snapshot.status.is_final:
                    return
        finally:
            subscribers = self._subscribers.get(job_id)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    del self._subscribers[job_id]

    async def shutdown(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        for task in list(self._tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task

    # --- internals ----------------------------------------------------------------

    async def _run(self, job_id: str, func: JobFunc) -> None:
        self._update(job_id, status=JobStatus.RUNNING, started=True)
        try:
            result = await func(JobContext(self, job_id))
        except asyncio.CancelledError:
            self._update(job_id, status=JobStatus.INTERRUPTED, failed_running_step=True)
            raise
        except (LLMError, UserError) as exc:
            self._update(
                job_id, status=JobStatus.FAILED, error=exc.message, failed_running_step=True
            )
        except Exception:
            logger.exception("Job %s failed", job_id)
            self._update(
                job_id, status=JobStatus.FAILED, error=GENERIC_ERROR, failed_running_step=True
            )
        else:
            self._update(job_id, status=JobStatus.SUCCEEDED, progress=100, result=result or {})

    def _update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        step: tuple[str, StepStatus] | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        started: bool = False,
        failed_running_step: bool = False,
    ) -> None:
        with Session(self._engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            steps = [dict(s) for s in job.steps]  # new list so SQLAlchemy sees the change
            if step is not None:
                key, step_status = step
                for item in steps:
                    if item["key"] == key:
                        item["status"] = step_status.value
            if failed_running_step:
                for item in steps:
                    if item["status"] == StepStatus.RUNNING.value:
                        item["status"] = StepStatus.FAILED.value
            job.steps = steps
            if progress is not None:
                job.progress = max(0, min(100, progress))
            if status is not None:
                job.status = status
                if status.is_final:
                    job.finished_at = utcnow()
            if started:
                job.started_at = utcnow()
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            session.add(job)
            session.commit()
            session.refresh(job)
            snapshot = JobRead.from_job(job)
        for queue in self._subscribers.get(job_id, ()):
            queue.put_nowait(snapshot)
