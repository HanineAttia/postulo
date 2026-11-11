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


PT_PER_MM = 72 / 25.4


def lowest_text_bottom(pdf: bytes) -> tuple[float, float]:
    """(bottom of the lowest printed character, page height) on the last page, in points."""
    document = pdfium.PdfDocument(pdf)
    try:
        page = document[len(document) - 1]
        height = page.get_height()
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        lowest = height
        for index in range(textpage.count_chars()):
            if index < len(text) and text[index].isspace():
                continue
            left, bottom, right, top = textpage.get_charbox(index)
            if right > left and top > bottom:
                lowest = min(lowest, bottom)
        textpage.close()
        page.close()
        return lowest, height
    finally:
        document.close()


def fill_ratio(pdf: bytes, doc: Document) -> float:
    """Share of the usable page height used by the text (last page), SPEC 16.1."""
    lowest, height = lowest_text_bottom(pdf)
    margin = doc.layout.margin_y * PT_PER_MM
    usable = height - 2 * margin
    return max(0.0, (height - margin - lowest) / usable) if usable > 0 else 0.0


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
