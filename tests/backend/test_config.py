from __future__ import annotations

import json
from pathlib import Path

import pytest

from postulo import config


def test_postulo_home_override(postulo_home: Path) -> None:
    assert config.data_dir() == postulo_home
    assert postulo_home.is_dir()
    assert config.db_path() == postulo_home / "postulo.db"


def test_default_dir_on_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("POSTULO_HOME")
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert config.data_dir() == tmp_path / "Roaming" / "Postulo"


def test_default_dir_on_linux(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("POSTULO_HOME")
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "share"))
    assert config.data_dir() == tmp_path / "share" / "postulo"


def test_path_with_spaces_and_accents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "Mes données été"
    monkeypatch.setenv("POSTULO_HOME", str(home))
    settings = config.Settings()
    config.save_settings(settings)
    assert config.load_settings() == settings
    assert (home / "settings.json").is_file()


def test_settings_defaults_to_demo_mode() -> None:
    settings = config.load_settings()
    assert settings.ai.provider == "mock"
    assert settings.demo_mode is True
    assert settings.ui.language == "fr"


def test_settings_round_trip() -> None:
    settings = config.Settings()
    settings.ai.provider = "anthropic_api"
    settings.ui.language = "en"
    config.save_settings(settings)
    loaded = config.load_settings()
    assert loaded.ai.provider == "anthropic_api"
    assert loaded.demo_mode is False
    assert json.loads(config.settings_path().read_text(encoding="utf-8"))["ui"]["language"] == "en"


def test_invalid_settings_file_falls_back_to_defaults() -> None:
    config.settings_path().write_text("{not json", encoding="utf-8")
    assert config.load_settings() == config.Settings()
