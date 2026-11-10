"""Shared fixtures: every test runs against a fresh, temporary data directory."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from postulo.db import session as db_session


@pytest.fixture(autouse=True)
def postulo_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    home = tmp_path / "postulo-home"
    monkeypatch.setenv("POSTULO_HOME", str(home))
    monkeypatch.delenv("POSTULO_DEV", raising=False)
    yield home
    db_session.dispose_engines()


@pytest.fixture
def migrated_db(postulo_home: Path) -> Path:
    db_session.init_db()
    return postulo_home / "postulo.db"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
