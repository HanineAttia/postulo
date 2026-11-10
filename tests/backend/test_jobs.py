from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from postulo.db.models import JobStatus, StepStatus
from postulo.db.session import get_engine
from postulo.services.demo import DEMO_STEPS, make_demo_job
from postulo.services.jobs import GENERIC_ERROR, JobContext, JobManager, JobRead
from postulo.services.llm.base import LLMError, LLMErrorKind
from postulo.services.llm.usage import calls_today

pytestmark = pytest.mark.anyio


async def _collect(manager: JobManager, job_id: str) -> list[JobRead]:
    return [snapshot async for snapshot in manager.subscribe(job_id)]


async def test_demo_job_reports_live_progress(migrated_db: Path) -> None:
    manager = JobManager(get_engine())
    job = manager.start("demo", DEMO_STEPS, make_demo_job(step_seconds=0.02))
    assert job.status is JobStatus.PENDING
    assert [s.key for s in job.steps] == list(DEMO_STEPS)

    snapshots = await asyncio.wait_for(_collect(manager, job.id), timeout=5)

    progress = [s.progress for s in snapshots]
    assert progress == sorted(progress), "progress never goes backwards"
    assert len(set(progress)) > len(DEMO_STEPS), "intermediate progress is reported"
    final = snapshots[-1]
    assert final.status is JobStatus.SUCCEEDED
    assert final.progress == 100
    assert all(s.status is StepStatus.DONE for s in final.steps)
    assert final.result is not None
    assert final.result["score"] == 82
    assert final.finished_at is not None
    assert calls_today() == 1  # the mock call is recorded


async def test_subscribe_to_finished_job_yields_final_state_once(migrated_db: Path) -> None:
    manager = JobManager(get_engine())

    async def quick(_ctx: JobContext) -> dict[str, Any]:
        return {"ok": True}

    job = manager.start("t", ["only"], quick)
    await asyncio.wait_for(_collect(manager, job.id), timeout=5)
    snapshots = await _collect(manager, job.id)
    assert len(snapshots) == 1
    assert snapshots[0].status is JobStatus.SUCCEEDED
    assert snapshots[0].result == {"ok": True}


async def test_llm_error_fails_job_with_user_message(migrated_db: Path) -> None:
    manager = JobManager(get_engine())

    async def failing(ctx: JobContext) -> dict[str, Any]:
        ctx.start_step("a")
        raise LLMError(LLMErrorKind.USAGE_LIMIT)

    job = manager.start("t", ["a", "b"], failing)
    final = (await asyncio.wait_for(_collect(manager, job.id), timeout=5))[-1]
    assert final.status is JobStatus.FAILED
    assert final.error is not None
    assert "plus tard" in final.error
    assert [s.status for s in final.steps] == [StepStatus.FAILED, StepStatus.PENDING]


async def test_unexpected_error_hides_traceback(migrated_db: Path) -> None:
    manager = JobManager(get_engine())

    async def crashing(_ctx: JobContext) -> dict[str, Any]:
        raise ValueError("secret internal detail")

    job = manager.start("t", [], crashing)
    final = (await asyncio.wait_for(_collect(manager, job.id), timeout=5))[-1]
    assert final.status is JobStatus.FAILED
    assert final.error == GENERIC_ERROR


async def test_shutdown_interrupts_running_jobs(migrated_db: Path) -> None:
    manager = JobManager(get_engine())

    async def slow(ctx: JobContext) -> dict[str, Any]:
        ctx.start_step("a")
        await asyncio.sleep(30)
        return {}

    job = manager.start("t", ["a"], slow)
    await asyncio.sleep(0.05)
    await manager.shutdown()
    stored = manager.get(job.id)
    assert stored is not None
    assert stored.status is JobStatus.INTERRUPTED
    assert stored.steps[0].status is StepStatus.FAILED


def test_unknown_job(migrated_db: Path) -> None:
    assert JobManager(get_engine()).get("nope") is None
