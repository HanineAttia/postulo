"""Export and import of the career library as JSON or YAML (backup, SPEC 6.2)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

import yaml

from postulo import APP_NAME
from postulo.services.profile.lenient import validate_lenient
from postulo.services.profile.schema import CareerProfile

BackupFormat = Literal["json", "yaml"]
FORMAT_VERSION = 1
MAX_BACKUP_BYTES = 5 * 1024 * 1024


class BackupError(ValueError):
    """User-facing error (French message)."""


def export_profile(profile: CareerProfile, fmt: BackupFormat) -> str:
    envelope: dict[str, Any] = {
        "app": APP_NAME,
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "profile": profile.model_dump(mode="json"),
    }
    if fmt == "yaml":
        return yaml.safe_dump(envelope, allow_unicode=True, sort_keys=False, width=100)
    return json.dumps(envelope, ensure_ascii=False, indent=2)


def parse_backup(content: bytes, filename: str = "") -> tuple[CareerProfile, list[str]]:
    """Read a JSON or YAML backup (envelope or bare profile). Invalid fields become warnings."""
    if len(content) > MAX_BACKUP_BYTES:
        raise BackupError("Le fichier est trop volumineux pour une sauvegarde de profil.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BackupError("Le fichier n'est pas un texte UTF-8.") from exc
    data: Any
    try:
        if filename.lower().endswith((".yaml", ".yml")):
            data = yaml.safe_load(text)
        else:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = yaml.safe_load(text)  # YAML is a superset of JSON
    except yaml.YAMLError as exc:
        raise BackupError("Le fichier n'est ni un JSON ni un YAML valide.") from exc
    if isinstance(data, dict) and isinstance(data.get("profile"), dict):
        version = data.get("format_version", FORMAT_VERSION)
        if isinstance(version, int) and version > FORMAT_VERSION:
            raise BackupError("Cette sauvegarde vient d'une version plus récente de Postulo.")
        data = data["profile"]
    if not isinstance(data, dict):
        raise BackupError("Le fichier ne contient pas de profil.")
    return validate_lenient(data)
