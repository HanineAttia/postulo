"""Paths and user settings.

User data never lives in the repository. Location:
- Windows: %APPDATA%/Postulo
- Linux / WSL / macOS: ~/.local/share/postulo (or $XDG_DATA_HOME/postulo)
- overridable with the POSTULO_HOME environment variable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from postulo import APP_NAME

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent

ProviderName = Literal["mock", "claude_code_cli", "anthropic_api", "openai_compatible"]


def data_dir() -> Path:
    """Return the user data directory, creating it if needed."""
    override = os.environ.get("POSTULO_HOME")
    if override:
        path = Path(override).expanduser()
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(appdata) / APP_NAME
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(xdg) / APP_NAME.lower()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "postulo.db"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def frontend_dist_dir() -> Path | None:
    """Locate the compiled frontend: bundled in the package, or built in the repo."""
    for candidate in (PACKAGE_DIR / "web", REPO_ROOT / "frontend" / "dist"):
        if (candidate / "index.html").is_file():
            return candidate
    return None


def is_dev_mode() -> bool:
    return os.environ.get("POSTULO_DEV") == "1"


class AISettings(BaseModel):
    provider: ProviderName = "mock"
    model: str | None = None
    timeout_seconds: int = Field(default=300, ge=10, le=1800)


class UISettings(BaseModel):
    language: Literal["fr", "en"] = "fr"
    theme: Literal["system", "light", "dark"] = "system"


class DocumentSettings(BaseModel):
    """Workshop defaults (SPEC 12.3, Réglages > documents)."""

    engine: Literal["typst", "html"] = "typst"
    template: Literal["modern", "classic"] = "modern"
    language: Literal["fr", "en"] = "fr"
    jury: bool = True
    revision: bool = True
    threshold: int = Field(default=82, ge=0, le=100)


class Settings(BaseModel):
    """Non-secret user settings persisted in settings.json. Secrets go to keyring."""

    ai: AISettings = Field(default_factory=AISettings)
    ui: UISettings = Field(default_factory=UISettings)
    documents: DocumentSettings = Field(default_factory=DocumentSettings)
    onboarding_completed: bool = False

    @property
    def demo_mode(self) -> bool:
        """Demo mode is on while no real AI provider is configured."""
        return self.ai.provider == "mock"


def load_settings() -> Settings:
    """Read settings.json. A missing or invalid file yields defaults (never prompts)."""
    path = settings_path()
    if not path.is_file():
        return Settings()
    try:
        return Settings.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError):
        return Settings()


def save_settings(settings: Settings) -> None:
    path = settings_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def database_url() -> str:
    return f"sqlite:///{db_path().as_posix()}"
