"""Preview of an import (CV or backup): what a merge or a replace would change."""

from __future__ import annotations

from pydantic import BaseModel

from postulo.services.profile import store
from postulo.services.profile.merge import ImportDiff, describe_replace, merge_profiles
from postulo.services.profile.schema import CareerProfile


class ImportPreview(BaseModel):
    """Nothing is saved until the user applies it (POST /api/profile/apply)."""

    base_version: int
    incoming: CareerProfile
    merge_diff: ImportDiff
    replace_diff: ImportDiff
    warnings: list[str]


def build_preview(incoming: CareerProfile, warnings: list[str]) -> ImportPreview:
    current = store.get_profile()
    _merged, merge_diff = merge_profiles(current.profile, incoming)
    return ImportPreview(
        base_version=current.version,
        incoming=incoming,
        merge_diff=merge_diff,
        replace_diff=describe_replace(current.profile, incoming),
        warnings=warnings,
    )
