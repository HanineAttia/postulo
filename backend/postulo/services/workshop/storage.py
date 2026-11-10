"""Application folders: drafts, documents, reports and PDFs (SPEC 7.4 step 8).

<data dir>/applications/<id>/
  offer.txt            sanitized offer text
  draft.json           the original AI draft, never modified
  revised_draft.json   the revision (when the jury asked for one)
  documents.json       full CV and letter (before compaction): what the user edits
  data.json            the compacted CV data given to the template
  report.json          warnings, keywords, ATS and jury reports
  CV_*.pdf, Lettre_*.pdf
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from postulo.config import data_dir
from postulo.services.documents.model import CvDocument, EngineName, LetterDocument
from postulo.services.quality.ats_check import AtsReport
from postulo.services.quality.jury import JuryReport

APPLICATIONS_DIRNAME = "applications"


class EditableDocuments(BaseModel):
    cv: CvDocument
    letter: LetterDocument


class ApplicationReport(BaseModel):
    warnings: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    removed_skills: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    ats_before: AtsReport | None = None  # first generation, before the revision
    ats: AtsReport | None = None  # current documents
    jury_before: JuryReport | None = None
    jury_after: JuryReport | None = None
    revision_applied: bool = False
    revision_kept: bool = False
    compaction_level: int = 0
    pages: int = 0
    target_pages: int = 1
    letter_pages: int = 0
    engine: EngineName = "typst"
    cv_file: str = ""
    letter_file: str = ""
    edited: bool = False


def applications_root() -> Path:
    root = data_dir() / APPLICATIONS_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def application_dir(application_id: str) -> Path:
    if not application_id.isalnum():  # ids are uuid hex: never a path
        raise ValueError("Invalid application id")
    folder = applications_root() / application_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_json(folder: Path, name: str, payload: BaseModel | dict[str, Any]) -> None:
    text = (
        payload.model_dump_json(indent=2)
        if isinstance(payload, BaseModel)
        else json.dumps(payload, ensure_ascii=False, indent=2)
    )
    tmp = folder / f"{name}.tmp"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(folder / name)


def read_report(folder: Path) -> ApplicationReport:
    path = folder / "report.json"
    if not path.is_file():
        return ApplicationReport()
    return ApplicationReport.model_validate_json(path.read_text(encoding="utf-8"))


def read_documents(folder: Path) -> EditableDocuments | None:
    path = folder / "documents.json"
    if not path.is_file():
        return None
    return EditableDocuments.model_validate_json(path.read_text(encoding="utf-8"))


def read_offer(folder: Path) -> str:
    path = folder / "offer.txt"
    return path.read_text(encoding="utf-8") if path.is_file() else ""
