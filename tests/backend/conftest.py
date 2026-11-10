"""Shared fixtures: every test runs against a fresh, temporary data directory."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest
from keyring.backend import KeyringBackend

from postulo.db import session as db_session


class MemoryKeyring(KeyringBackend):
    """In-memory keyring: tests never touch the real system credential manager."""

    priority = 1

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.store.pop((service, username), None)


@pytest.fixture(autouse=True)
def postulo_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    home = tmp_path / "postulo-home"
    monkeypatch.setenv("POSTULO_HOME", str(home))
    monkeypatch.delenv("POSTULO_DEV", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    previous = keyring.get_keyring()
    keyring.set_keyring(MemoryKeyring())
    yield home
    keyring.set_keyring(previous)
    db_session.dispose_engines()


@pytest.fixture
def migrated_db(postulo_home: Path) -> Path:
    db_session.init_db()
    return postulo_home / "postulo.db"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
