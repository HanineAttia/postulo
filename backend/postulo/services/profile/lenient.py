"""Tolerant validation of imported data (CV structured by the AI, backup files).

Strict validation would reject a whole CV for one odd date. Here, every invalid
field is dropped (its default applies) and reported as a warning, so the user
sees what was left out in the preview.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import ValidationError

from postulo.services.profile.schema import CareerProfile

_MAX_FIXES = 200


def validate_lenient(data: Any) -> tuple[CareerProfile, list[str]]:
    """Validate `data` as a CareerProfile, dropping invalid fields. Returns (profile, warnings)."""
    if not isinstance(data, dict):
        return CareerProfile(), ["Le contenu importé n'est pas un profil (objet JSON attendu)."]
    current: dict[str, Any] = copy.deepcopy(data)
    warnings: list[str] = []
    for _ in range(_MAX_FIXES):
        try:
            return CareerProfile.model_validate(current), warnings
        except ValidationError as exc:
            fixed = False
            for error in exc.errors():
                location = tuple(error["loc"])
                if _drop(current, location):
                    warnings.append(f"Champ ignoré ({_path(location)}) : {error['msg']}")
                    fixed = True
            if not fixed:
                break
    return CareerProfile(), [*warnings, "Le profil importé n'a pas pu être lu."]


def _drop(data: Any, location: tuple[int | str, ...]) -> bool:
    """Remove the value at `location` from nested dicts/lists. Returns True if removed."""
    if not location:
        return False
    parent = data
    for key in location[:-1]:
        try:
            parent = parent[key]
        except (KeyError, IndexError, TypeError):
            return False
    last = location[-1]
    if isinstance(parent, dict) and last in parent:
        del parent[last]
        return True
    if isinstance(parent, list) and isinstance(last, int) and 0 <= last < len(parent):
        del parent[last]
        return True
    return False


def _path(location: tuple[int | str, ...]) -> str:
    return ".".join(str(part) for part in location)
