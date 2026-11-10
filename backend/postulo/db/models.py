"""SQLModel tables.

Phase 0 defines only the tables it needs (jobs, AI usage, profile). The other
tables of docs/SPEC.md section 4 arrive with their phase, through new migrations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


def _ts(nullable: bool = False, index: bool = False) -> Any:
    return Column(DateTime(timezone=True), nullable=nullable, index=index)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

    @property
    def is_final(self) -> bool:
        return self not in (JobStatus.PENDING, JobStatus.RUNNING)


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Job(SQLModel, table=True):
    """A background task (application generation, multi-source search, watch...)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    type: str = Field(index=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    progress: int = 0
    # List of {"key": str, "status": StepStatus}. Labels are translated by the frontend.
    steps: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_column=_ts())
    started_at: datetime | None = Field(default=None, sa_column=_ts(nullable=True))
    finished_at: datetime | None = Field(default=None, sa_column=_ts(nullable=True))


class LLMUsage(SQLModel, table=True):
    """One AI call. Feeds the daily counter shown in the header."""

    __tablename__ = "llm_usage"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, sa_column=_ts(index=True))
    provider: str
    task: str
    duration_ms: int
    success: bool
    error_kind: str | None = None


class Profile(SQLModel, table=True):
    """The single-row career library. `data` holds the validated JSON (phase 1 schema)."""

    id: int | None = Field(default=None, primary_key=True)
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    version: int = 1
    updated_at: datetime = Field(default_factory=utcnow, sa_column=_ts())
