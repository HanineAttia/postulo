from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import Session

from postulo.db import session as db_session
from postulo.db.models import Job, JobStatus, LLMUsage


def test_migrations_create_tables(migrated_db: Path) -> None:
    assert migrated_db.is_file()
    tables = set(inspect(db_session.get_engine()).get_table_names())
    assert {"job", "llm_usage", "profile", "alembic_version"} <= tables


def test_migrations_are_idempotent(migrated_db: Path) -> None:
    db_session.init_db()
    db_session.init_db()


def test_models_match_latest_migration(migrated_db: Path) -> None:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlmodel import SQLModel

    with db_session.get_engine().connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
    assert diff == []


def test_job_json_round_trip(migrated_db: Path) -> None:
    with Session(db_session.get_engine()) as s:
        job = Job(type="demo", steps=[{"key": "draft", "status": "pending"}], result={"a": "é"})
        s.add(job)
        s.commit()
        job_id = job.id
    with Session(db_session.get_engine()) as s:
        loaded = s.get(Job, job_id)
        assert loaded is not None
        assert loaded.status is JobStatus.PENDING
        assert loaded.steps == [{"key": "draft", "status": "pending"}]
        assert loaded.result == {"a": "é"}


def test_running_jobs_are_interrupted_on_startup(migrated_db: Path) -> None:
    with Session(db_session.get_engine()) as s:
        s.add(Job(id="r", type="demo", status=JobStatus.RUNNING))
        s.add(Job(id="d", type="demo", status=JobStatus.SUCCEEDED))
        s.commit()
    assert db_session.mark_interrupted_jobs() == 1
    with Session(db_session.get_engine()) as s:
        running = s.get(Job, "r")
        done = s.get(Job, "d")
        assert running is not None
        assert running.status is JobStatus.INTERRUPTED
        assert running.finished_at is not None
        assert done is not None
        assert done.status is JobStatus.SUCCEEDED


def test_llm_usage_insert(migrated_db: Path) -> None:
    with Session(db_session.get_engine()) as s:
        s.add(LLMUsage(provider="mock", task="demo", duration_ms=3, success=True))
        s.commit()
