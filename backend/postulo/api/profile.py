"""Career library: read, save, completeness, sample, backup, imports (SPEC 6)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from postulo.services.profile import store
from postulo.services.profile.backup import BackupError, BackupFormat, export_profile, parse_backup
from postulo.services.profile.completeness import Completeness, compute_completeness
from postulo.services.profile.merge import ImportDiff, describe_replace, merge_profiles
from postulo.services.profile.sample import sample_profile
from postulo.services.profile.schema import CareerProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])

CONFLICT_MESSAGE = (
    "Ton parcours a été modifié ailleurs (autre onglet ou import). Recharge la page avant "
    "d'enregistrer."
)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class ProfileUpdate(BaseModel):
    version: int
    profile: CareerProfile


class SampleRequest(BaseModel):
    force: bool = False


class ImportPreview(BaseModel):
    """What an import would change. Nothing is saved until /apply."""

    base_version: int
    incoming: CareerProfile
    merge_diff: ImportDiff
    replace_diff: ImportDiff
    warnings: list[str]


class ApplyImport(BaseModel):
    mode: Literal["merge", "replace"]
    incoming: CareerProfile
    version: int


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


def _save(profile: CareerProfile, version: int) -> store.StoredProfile:
    try:
        return store.save_profile(profile, expected_version=version)
    except store.VersionConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, CONFLICT_MESSAGE) from exc


async def read_upload(file: UploadFile, limit: int = MAX_UPLOAD_BYTES) -> bytes:
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Le fichier dépasse {limit // (1024 * 1024)} Mo.",
        )
    return content


@router.get("")
def read_profile() -> store.StoredProfile:
    return store.get_profile()


@router.put("")
def update_profile(body: ProfileUpdate) -> store.StoredProfile:
    return _save(body.profile, body.version)


@router.get("/completeness")
def read_completeness() -> Completeness:
    return compute_completeness(store.get_profile().profile)


@router.post("/sample")
def load_sample(body: SampleRequest) -> store.StoredProfile:
    current = store.get_profile()
    if current.profile.has_content() and not body.force:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ton parcours contient déjà des informations. Confirme pour le remplacer par le "
            "profil d'exemple.",
        )
    return store.save_profile(sample_profile())


@router.get("/export")
def export(format: BackupFormat = "json") -> Response:
    content = export_profile(store.get_profile().profile, format)
    filename = f"postulo-parcours-{date.today().isoformat()}.{format}"
    media_type = "application/json" if format == "json" else "application/yaml"
    return Response(
        content=content.encode("utf-8"),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import-backup")
async def import_backup(file: UploadFile) -> ImportPreview:
    content = await read_upload(file)
    try:
        incoming, warnings = parse_backup(content, file.filename or "")
    except BackupError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return build_preview(incoming, warnings)


@router.post("/apply")
def apply_import(body: ApplyImport) -> store.StoredProfile:
    """Merge (no duplicates) or replace, against the current saved profile."""
    current = store.get_profile()
    if body.mode == "replace":
        result = body.incoming
    else:
        result, _diff = merge_profiles(current.profile, body.incoming)
    return _save(result, body.version)
