"""PDF rendering (docs/SPEC.md section 7.5).

Main engine: Typst, through the `typst` Python package (typst-py), with the
fonts bundled in `assets/fonts` and system fonts ignored, so a PDF looks the
same on every machine. The template reads `data.json`: texts are never escaped
nor interpreted as markup. Fallback engine: HTML (html_engine.py).

Rendering is CPU-bound and synchronous: async callers use `asyncio.to_thread`.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pypdfium2 as pdfium
import typst

from postulo.errors import UserError
from postulo.services.documents.model import CvDocument, EngineName, LetterDocument

PACKAGE_DIR = Path(__file__).resolve().parents[2]
FONTS_DIR = PACKAGE_DIR / "assets" / "fonts"
TYPST_DIR = PACKAGE_DIR / "templates" / "typst"

DocKind = Literal["cv", "letter"]
Document = CvDocument | LetterDocument


class RenderError(UserError):
    """The PDF could not be produced (French message, technical detail apart)."""


@dataclass(frozen=True)
class RenderedPdf:
    data: bytes
    pages: int
    engine: EngineName


def document_data(doc: Document) -> dict[str, Any]:
    """The JSON given to the templates (also saved as data.json for traceability)."""
    data = doc.model_dump(mode="json")
    data["meta_title"] = doc.meta_title
    return data


def page_count(pdf: bytes) -> int:
    document = pdfium.PdfDocument(pdf)
    try:
        return len(document)
    finally:
        document.close()


def render_typst(doc: Document, kind: DocKind) -> bytes:
    with tempfile.TemporaryDirectory(prefix="postulo-typst-") as tmp:
        root = Path(tmp)
        shutil.copy(TYPST_DIR / "common.typ", root / "common.typ")
        shutil.copy(TYPST_DIR / f"{kind}.typ", root / "main.typ")
        (root / "data.json").write_text(
            json.dumps(document_data(doc), ensure_ascii=False), encoding="utf-8"
        )
        try:
            compiler = typst.Compiler(
                root=str(root), font_paths=[str(FONTS_DIR)], ignore_system_fonts=True
            )
            result = compiler.compile(input=str(root / "main.typ"), format="pdf")
        except typst.TypstError as exc:
            raise RenderError(
                "La mise en page du document a échoué.", detail=f"{exc.message} {exc.hints}"
            ) from exc
    if not isinstance(result, bytes):  # pragma: no cover - PDF output is always one file
        raise RenderError("La mise en page du document a échoué.", detail="unexpected output")
    return result


def render_pdf(doc: Document, kind: DocKind, engine: EngineName = "typst") -> RenderedPdf:
    if engine == "html":
        from postulo.services.documents.html_engine import render_html

        data = render_html(doc, kind)
    else:
        data = render_typst(doc, kind)
    return RenderedPdf(data=data, pages=page_count(data), engine=engine)
