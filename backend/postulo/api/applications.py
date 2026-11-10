"""Application workshop API (docs/SPEC.md sections 7 and 12.3 "Atelier")."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from postulo.config import load_settings
from postulo.db.models import Application, ApplicationStatus, utcnow
from postulo.db.session import get_engine
from postulo.errors import UserError
from postulo.services.documents.model import DocLang, EngineName, TemplateName
from postulo.services.jobs import JobManager, JobRead
from postulo.services.llm import registry
from postulo.services.llm.base import LLMError, LLMErrorKind, LLMProvider
from postulo.services.llm.providers.mock import MockProvider
from postulo.services.profile import store
from postulo.services.workshop.pipeline import (
    APPLICATION_JOB_TYPE,
    APPLICATION_STEPS,
    WorkshopOptions,
    make_application_job,
    regenerate,
)
from postulo.services.workshop.storage import (
    ApplicationReport,
    EditableDocuments,
    read_documents,
    read_offer,
    read_report,
)

router = APIRouter(prefix="/api/applications", tags=["applications"])

MIN_OFFER_CHARS = 80
MAX_OFFER_CHARS = 60_000
NOT_FOUND = "Candidature introuvable."


class ApplicationCreate(BaseModel):
    offer_text: str = Field(max_length=MAX_OFFER_CHARS)
    organization: str = Field(default="", max_length=200)
    position: str = Field(default="", max_length=200)
    lang: DocLang | None = None
    template: TemplateName | None = None
    engine: EngineName | None = None
    jury: bool | None = None
    revision: bool | None = None
    threshold: int | None = Field(default=None, ge=0, le=100)


class ApplicationSummary(BaseModel):
    id: str
    organization: str
    position: str
    status: ApplicationStatus
    lang: str
    template: str
    ats_score: int | None
    jury_score_before: int | None
    jury_score_after: int | None
    compaction_level: int | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: Application) -> ApplicationSummary:
        return cls.model_validate(row, from_attributes=True)


class ApplicationDetail(ApplicationSummary):
    email_subject: str
    email_body: str
    offer_text: str
    report: ApplicationReport
    documents: EditableDocuments | None
    files: dict[str, str]


class DocumentsUpdate(BaseModel):
    documents: EditableDocuments
    email_subject: str = Field(default="", max_length=300)
    email_body: str = Field(default="", max_length=5000)


class SampleOffer(BaseModel):
    text: str


def _get(application_id: str) -> Application:
    with Session(get_engine()) as session:
        row = session.get(Application, application_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return row


def _detail(row: Application) -> ApplicationDetail:
    folder = Path(row.folder)
    report = read_report(folder)
    base = f"/api/applications/{row.id}/files"
    files = {}
    if report.cv_file:
        files["cv"] = f"{base}/cv"
    if report.letter_file:
        files["letter"] = f"{base}/letter"
    return ApplicationDetail(
        **ApplicationSummary.from_row(row).model_dump(),
        email_subject=row.email_subject,
        email_body=row.email_body,
        offer_text=read_offer(folder),
        report=report,
        documents=read_documents(folder),
        files=files,
    )


@router.get("/sample-offer")
def sample_offer() -> SampleOffer:
    """A fictional offer for the demo mode (never a real organization)."""
    text = resources.files("postulo").joinpath("data/sample_offer.txt").read_text("utf-8")
    return SampleOffer(text=text)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_application(body: ApplicationCreate, request: Request) -> JobRead:
    if len(body.offer_text.strip()) < MIN_OFFER_CHARS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Colle le texte complet de l'offre (missions et profil recherché).",
        )
    profile = store.get_profile().profile
    if not (profile.experiences or profile.projects or profile.education):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ton parcours est vide : remplis « Mon parcours » ou charge le profil d'exemple.",
        )
    settings = load_settings()
    defaults = settings.documents
    options = WorkshopOptions(
        lang=body.lang or defaults.language,
        template=body.template or defaults.template,
        engine=body.engine or defaults.engine,
        jury=defaults.jury if body.jury is None else body.jury,
        revision=defaults.revision if body.revision is None else body.revision,
        threshold=defaults.threshold if body.threshold is None else body.threshold,
        organization=body.organization,
        position=body.position,
    )
    if settings.demo_mode:
        # Demo mode: a short pause per AI call, so the live progress stays visible.
        delay = float(getattr(request.app.state, "demo_step_seconds", 0.0)) * 0.6
        provider: LLMProvider = MockProvider(delay=delay)
    else:
        provider = registry.get_provider(settings)
    available, reason = provider.available()
    if not available:
        raise LLMError(LLMErrorKind.NOT_AVAILABLE, reason)
    manager: JobManager = request.app.state.jobs
    job = make_application_job(
        application_id=uuid.uuid4().hex,
        profile=profile,
        offer_text=body.offer_text,
        options=options,
        provider=provider,
        timeout=settings.ai.timeout_seconds,
    )
    return manager.start(APPLICATION_JOB_TYPE, APPLICATION_STEPS, job)


@router.get("")
def list_applications(limit: int = 50) -> list[ApplicationSummary]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(Application).order_by(col(Application.created_at).desc()).limit(limit)
        ).all()
    return [ApplicationSummary.from_row(row) for row in rows]


@router.get("/{application_id}")
def read_application(application_id: str) -> ApplicationDetail:
    return _detail(_get(application_id))


@router.get("/{application_id}/files/{kind}")
def read_file(
    application_id: str, kind: Literal["cv", "letter"], download: bool = False
) -> FileResponse:
    row = _get(application_id)
    folder = Path(row.folder)
    report = read_report(folder)
    name = report.cv_file if kind == "cv" else report.letter_file
    path = folder / name
    # Names come from report.json, written by the app; still refuse anything outside the folder.
    if not name or path.parent != folder or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document introuvable.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=name,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "no-store"},
    )


@router.put("/{application_id}/documents")
async def update_documents(application_id: str, body: DocumentsUpdate) -> ApplicationDetail:
    """Save the user's edits and regenerate the PDFs, without any AI call."""
    row = _get(application_id)
    profile = store.get_profile().profile
    try:
        await run_in_threadpool(
            regenerate,
            row,
            body.documents,
            profile=profile,
            email_subject=body.email_subject,
            email_body=body.email_body,
        )
    except UserError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.message) from exc
    return _detail(_get(application_id))


@router.post("/{application_id}/sent")
def mark_sent(application_id: str) -> ApplicationDetail:
    """The user sent the application herself (the app never sends anything)."""
    with Session(get_engine()) as session:
        row = session.get(Application, application_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
        row.status = ApplicationStatus.SENT
        row.sent_at = row.sent_at or utcnow()
        row.updated_at = utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
    return _detail(row)


@router.post("/{application_id}/open-folder", status_code=status.HTTP_204_NO_CONTENT)
def open_folder(application_id: str) -> Response:
    """Open the application folder in the file explorer (the server runs on this machine)."""
    folder = Path(_get(application_id).folder)
    if not folder.is_dir():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dossier introuvable.")
    # os.startfile only exists on Windows (getattr keeps mypy happy on every platform).
    startfile = getattr(os, "startfile", None)
    if startfile is not None:
        startfile(folder)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, str(folder)])  # noqa: S603
    return Response(status_code=status.HTTP_204_NO_CONTENT)
