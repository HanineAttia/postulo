"""Career library: read, save, completeness, sample, backup, imports (SPEC 6)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel

from postulo.config import load_settings
from postulo.services.jobs import JobManager, JobRead
from postulo.services.llm import registry
from postulo.services.llm.base import LLMError, LLMErrorKind
from postulo.services.profile import store
from postulo.services.profile.backup import BackupError, BackupFormat, export_profile, parse_backup
from postulo.services.profile.completeness import Completeness, compute_completeness
from postulo.services.profile.cv_import import (
    CV_IMPORT_JOB_TYPE,
    CV_IMPORT_STEPS,
    CVImportError,
    extract_text,
    make_cv_import_job,
)
from postulo.services.profile.merge import merge_profiles
from postulo.services.profile.preview import ImportPreview, build_preview
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


class ApplyImport(BaseModel):
    mode: Literal["merge", "replace"]
    incoming: CareerProfile
    version: int


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


@router.post("/import-cv", status_code=status.HTTP_202_ACCEPTED)
async def import_cv(file: UploadFile, request: Request) -> JobRead:
    """Extract the CV text now (fast errors), then structure it with the AI in a job."""
    content = await read_upload(file)
    try:
        text = await run_in_threadpool(extract_text, file.filename or "", content)
    except CVImportError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    settings = load_settings()
    provider = registry.get_provider(settings)
    available, reason = provider.available()
    if not available:
        raise LLMError(LLMErrorKind.NOT_AVAILABLE, reason)
    manager: JobManager = request.app.state.jobs
    job = make_cv_import_job(text, provider, timeout=settings.ai.timeout_seconds)
    return manager.start(CV_IMPORT_JOB_TYPE, CV_IMPORT_STEPS, job)
