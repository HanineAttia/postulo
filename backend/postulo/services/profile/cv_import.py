"""CV import (docs/SPEC.md section 6.2): text extraction, AI structuring, preview.

Nothing is saved here: the job result is a preview (proposed profile + diff
against the current library). The user then chooses "merge" or "replace",
which goes through `POST /api/profile/apply`.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePath
from typing import Any
from xml.etree import ElementTree as ET

import pypdfium2 as pdfium
from pydantic import RootModel

from postulo.services import prompts
from postulo.services.jobs import JobContext, JobFunc
from postulo.services.llm.base import LLMProvider
from postulo.services.llm.json_utils import complete_json
from postulo.services.profile.lenient import validate_lenient
from postulo.services.profile.preview import build_preview
from postulo.services.prompts.sanitize import sanitize_text

CV_IMPORT_JOB_TYPE = "cv_import"
CV_IMPORT_STEPS = ("extract", "structure", "compare")
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")
MAX_CV_BYTES = 10 * 1024 * 1024
MAX_CV_CHARS = 30_000
# Below this many characters per page, a PDF is most likely a scan (an image).
_MIN_CHARS_PER_PAGE = 40
_MIN_TOTAL_CHARS = 80
_DOCX_MAX_XML_BYTES = 20 * 1024 * 1024

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class CVImportError(ValueError):
    """User-facing import error (French message)."""


class RawProfile(RootModel[dict[str, Any]]):
    """The AI answer before tolerant validation (see lenient.py)."""


# --- text extraction ------------------------------------------------------------------------


def extract_text(filename: str, content: bytes) -> str:
    """Return the text of a PDF, DOCX or TXT CV. Raise CVImportError when unusable."""
    if len(content) > MAX_CV_BYTES:
        raise CVImportError("Le fichier dépasse 10 Mo.")
    extension = PurePath(filename).suffix.lower()
    if extension == ".pdf":
        text = _pdf_text(content)
    elif extension == ".docx":
        text = _docx_text(content)
    elif extension in (".txt", ".md"):
        text = _plain_text(content)
    elif extension == ".doc":
        raise CVImportError(
            "Le format .doc (Word 97-2003) n'est pas pris en charge. Enregistre ton CV en "
            ".docx ou en PDF."
        )
    else:
        raise CVImportError("Format non pris en charge. Utilise un fichier PDF, DOCX ou TXT.")
    text = _tidy(text)
    if len(text) < _MIN_TOTAL_CHARS:
        raise CVImportError("Le fichier ne contient presque pas de texte lisible.")
    return text


def _pdf_text(content: bytes) -> str:
    try:
        document = pdfium.PdfDocument(content)
    except pdfium.PdfiumError as exc:
        raise CVImportError(
            "Ce PDF n'a pas pu être ouvert (fichier abîmé ou protégé par mot de passe)."
        ) from exc
    try:
        pages: list[str] = []
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_bounded())
            textpage.close()
            page.close()
    finally:
        document.close()
    total = sum(len(re.sub(r"\s", "", page)) for page in pages)
    if not pages or total < _MIN_CHARS_PER_PAGE * len(pages):
        raise CVImportError(
            "Ce PDF semble être une image (CV scanné) : son texte n'est pas lisible. Exporte ton "
            "CV en PDF depuis ton traitement de texte, ou importe le fichier DOCX."
        )
    return "\n\n".join(pages)


def _docx_text(content: bytes) -> str:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        info = archive.getinfo("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise CVImportError("Ce fichier DOCX n'a pas pu être lu.") from exc
    if info.file_size > _DOCX_MAX_XML_BYTES:
        raise CVImportError("Ce fichier DOCX est trop volumineux.")
    links: dict[str, str] = {}
    try:
        rels = ET.fromstring(archive.read("word/_rels/document.xml.rels"))  # noqa: S314
        for rel in rels.iter(f"{_REL}Relationship"):
            if rel.get("TargetMode") == "External" and rel.get("Id") and rel.get("Target"):
                links[rel.get("Id", "")] = rel.get("Target", "")
    except (KeyError, ET.ParseError):
        pass
    try:
        root = ET.fromstring(archive.read(info))  # noqa: S314
    except ET.ParseError as exc:
        raise CVImportError("Ce fichier DOCX est abîmé.") from exc
    paragraphs = [_docx_paragraph(p, links) for p in root.iter(f"{_W}p")]
    return "\n".join(paragraphs)


def _docx_paragraph(paragraph: ET.Element, links: dict[str, str]) -> str:
    parts: list[str] = []

    def walk(element: ET.Element) -> None:
        for child in element:
            if child.tag == f"{_W}t":
                parts.append(child.text or "")
            elif child.tag == f"{_W}tab":
                parts.append("\t")
            elif child.tag in (f"{_W}br", f"{_W}cr"):
                parts.append("\n")
            elif child.tag == f"{_W}hyperlink":
                before = len(parts)
                walk(child)
                url = links.get(child.get(f"{_R}id", ""), "")
                label = "".join(parts[before:])
                if url and url not in label:
                    parts.append(f" ({url})")
            elif child.tag != f"{_W}p":  # nested paragraphs are visited by root.iter
                walk(child)

    walk(paragraph)
    return "".join(parts)


def _plain_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CVImportError("L'encodage de ce fichier texte n'est pas reconnu.")  # pragma: no cover


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# --- AI structuring (background job) ---------------------------------------------------------


def build_cv_prompt(cv_text: str) -> tuple[str, list[str]]:
    sanitized = sanitize_text(cv_text, max_chars=MAX_CV_CHARS)
    return prompts.render("cv_extract", cv_text=sanitized.text), sanitized.warnings


def make_cv_import_job(cv_text: str, provider: LLMProvider, *, timeout: int = 300) -> JobFunc:
    async def run(ctx: JobContext) -> dict[str, Any]:
        ctx.start_step("extract")
        prompt, warnings = build_cv_prompt(cv_text)
        ctx.finish_step("extract", progress=10)
        ctx.start_step("structure")
        raw = await complete_json(provider, prompt, RawProfile, timeout=timeout)
        ctx.finish_step("structure", progress=90)
        ctx.start_step("compare")
        incoming, lenient_warnings = validate_lenient(raw.root)
        preview = build_preview(incoming, [*warnings, *lenient_warnings])
        ctx.finish_step("compare", progress=100)
        return preview.model_dump(mode="json")

    return run
