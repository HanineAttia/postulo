"""SQLModel tables.

Phase 0 defines only the tables it needs (jobs, AI usage, profile); phase 2 adds
`application`. The other tables of docs/SPEC.md section 4 arrive with their phase,
through new migrations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Dialect
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Store datetimes as UTC and always return timezone-aware values.

    SQLite has no timezone support: without this, values come back naive and the
    frontend would read them as local time.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed; use postulo.db.models.utcnow().")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def _ts(nullable: bool = False, index: bool = False) -> Any:
    return Column(UTCDateTime(), nullable=nullable, index=index)


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


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    FOLLOWED_UP = "followed_up"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER_RECEIVED = "offer_received"
    NO_ANSWER = "no_answer"
    WITHDRAWN = "withdrawn"


class Application(SQLModel, table=True):
    """One prepared application. Documents, drafts and reports live in its folder.

    `offer_id` and `organization_id` stay plain columns until the `offer` and
    `organization` tables arrive (phase 3).
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    offer_id: str | None = Field(default=None, index=True)
    organization_id: int | None = None
    organization: str = ""
    position: str = ""
    type: str = "offer"  # offer, spontaneous, referral, talent_pool
    channel: str = ""
    status: ApplicationStatus = Field(default=ApplicationStatus.DRAFT, index=True)
    lang: str = "fr"
    template: str = "modern"
    engine: str = "typst"
    folder: str  # absolute path of the application folder
    email_subject: str = ""
    email_body: str = ""
    ats_score: int | None = None
    jury_score_before: int | None = None
    jury_score_after: int | None = None
    compaction_level: int | None = None
    job_id: str | None = None
    notes: str = ""
    sent_at: datetime | None = Field(default=None, sa_column=_ts(nullable=True))
    created_at: datetime = Field(default_factory=utcnow, sa_column=_ts(index=True))
    updated_at: datetime = Field(default_factory=utcnow, sa_column=_ts())
