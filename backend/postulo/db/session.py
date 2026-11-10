"""Engine, sessions and schema migrations.

SQLAlchemy is used synchronously on purpose: SQLite is local and fast, and the
async extension would pull in greenlet for no benefit.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, event, update
from sqlmodel import Session, create_engine

from postulo import config
from postulo.db.models import Job, JobStatus, utcnow

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_engines: dict[str, Engine] = {}


def _set_sqlite_pragmas(dbapi_conn: Any, _record: Any) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def get_engine(url: str | None = None) -> Engine:
    """Return a cached engine for the given URL (default: the user database)."""
    url = url or config.database_url()
    engine = _engines.get(url)
    if engine is None:
        engine = create_engine(url, connect_args={"check_same_thread": False})
        event.listen(engine, "connect", _set_sqlite_pragmas)
        _engines[url] = engine
    return engine


def dispose_engines() -> None:
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()


def alembic_config(url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", url or config.database_url())
    return cfg


def run_migrations(url: str | None = None) -> None:
    """Upgrade the database schema to the latest revision."""
    engine = get_engine(url)
    with engine.begin() as connection:
        cfg = alembic_config(url)
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def mark_interrupted_jobs(url: str | None = None) -> int:
    """Jobs left running by a previous process can never finish: flag them."""
    with Session(get_engine(url)) as session:
        result = session.execute(
            update(Job)
            .where(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))  # type: ignore[attr-defined]
            .values(status=JobStatus.INTERRUPTED, finished_at=utcnow())
        )
        session.commit()
        return int(getattr(result, "rowcount", 0) or 0)


def init_db(url: str | None = None) -> None:
    run_migrations(url)
    mark_interrupted_jobs(url)


def get_session() -> Iterator[Session]:
    """FastAPI dependency."""
    with Session(get_engine()) as session:
        yield session
