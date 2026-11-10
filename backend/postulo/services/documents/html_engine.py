"""HTML fallback engine (docs/SPEC.md section 7.5).

Same documents, rendered from Jinja2 templates with the same ATS rules in CSS
(`font-variant-ligatures: none`, `hyphens: none`, one column, real links), then
printed to PDF by a Chromium browser:
1. Playwright's Chromium, only if the optional `playwright` package is installed
   (`uv sync --extra html`, then `playwright install chromium`);
2. otherwise Microsoft Edge (installed with Windows), then Google Chrome, driven
   on the command line (`--headless --print-to-pdf`), with a throwaway profile and
   background networking disabled. Templates are auto-escaped and contain no script.

Typst stays the main engine; this one exists for machines where Typst cannot run.
A LaTeX engine (SPEC 7.5, optional) is not implemented.  TODO(latex)
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pypdf import PdfReader, PdfWriter

from postulo.services.documents.model import CvDocument
from postulo.services.documents.render import (
    FONTS_DIR,
    PACKAGE_DIR,
    DocKind,
    Document,
    RenderError,
    document_data,
)

HTML_DIR = PACKAGE_DIR / "templates" / "html"
BROWSER_TIMEOUT_SECONDS = 60

_ENV = Environment(
    loader=FileSystemLoader(HTML_DIR),
    autoescape=select_autoescape(["j2", "html"], default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)

# (family, file name, CSS weight, CSS style)
_FONT_FILES: tuple[tuple[str, str, int, str], ...] = (
    ("Inter", "inter/Inter-Regular.ttf", 400, "normal"),
    ("Inter", "inter/Inter-Italic.ttf", 400, "italic"),
    ("Inter", "inter/Inter-SemiBold.ttf", 600, "normal"),
    ("Inter", "inter/Inter-Bold.ttf", 700, "normal"),
    ("Inter", "inter/Inter-BoldItalic.ttf", 700, "italic"),
    ("Source Serif 4", "source-serif-4/SourceSerif4-Regular.ttf", 400, "normal"),
    ("Source Serif 4", "source-serif-4/SourceSerif4-It.ttf", 400, "italic"),
    ("Source Serif 4", "source-serif-4/SourceSerif4-Semibold.ttf", 600, "normal"),
    ("Source Serif 4", "source-serif-4/SourceSerif4-Bold.ttf", 700, "normal"),
    ("Source Serif 4", "source-serif-4/SourceSerif4-BoldIt.ttf", 700, "italic"),
)

_WINDOWS_BROWSERS = (
    r"Microsoft\Edge\Application\msedge.exe",
    r"Google\Chrome\Application\chrome.exe",
)
_PATH_BROWSERS = ("msedge", "microsoft-edge", "google-chrome", "chrome", "chromium")


def render_html_source(doc: Document, kind: DocKind) -> str:
    fonts: dict[str, list[tuple[int, str, str]]] = {}
    for family, name, weight, style in _FONT_FILES:
        fonts.setdefault(family, []).append((weight, style, (FONTS_DIR / name).as_uri()))
    context: dict[str, Any] = {
        "d": document_data(doc),
        "L": doc.layout.model_dump(),
        "fonts": fonts,
        "subtitle": doc.title if isinstance(doc, CvDocument) else "",
        "label_sep": " : " if doc.lang == "fr" else ": ",
    }
    return _ENV.get_template(f"{kind}.html.j2").render(**context)


def find_browser() -> Path | None:
    """Edge first (always present on Windows 10/11), then Chrome."""
    roots = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    for relative in _WINDOWS_BROWSERS:
        for root in roots:
            if root and (candidate := Path(root) / relative).is_file():
                return candidate
    for name in _PATH_BROWSERS:
        if found := shutil.which(name):
            return Path(found)
    return None


def browser_command(
    prefix: list[str], html_file: Path, pdf_file: Path, profile_dir: Path
) -> list[str]:
    return [
        *prefix,
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        # No sync, updates nor background requests: rendering never needs the network.
        "--disable-sync",
        "--disable-background-networking",
        "--disable-component-update",
        f"--user-data-dir={profile_dir}",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_file}",
        html_file.as_uri(),
    ]


def _print_with_playwright(html_file: Path) -> bytes | None:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(java_script_enabled=False)
            page.goto(html_file.as_uri())
            data: bytes = page.pdf(prefer_css_page_size=True, print_background=True)
            browser.close()
            return data
    except Exception:  # Chromium not downloaded, etc.: fall back to Edge/Chrome
        return None


def _with_metadata(pdf: bytes, doc: Document) -> bytes:
    """Browsers only write the title: add the author too (SPEC 7.2)."""
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    writer.add_metadata({"/Title": doc.meta_title, "/Author": doc.name})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def render_html(doc: Document, kind: DocKind, *, browser: list[str] | None = None) -> bytes:
    """Print `doc` to PDF. `browser` is a command prefix (tests use a fake browser)."""
    return _with_metadata(_print(doc, kind, browser), doc)


def _print(doc: Document, kind: DocKind, browser: list[str] | None) -> bytes:
    with tempfile.TemporaryDirectory(prefix="postulo-html-") as tmp:
        root = Path(tmp)
        html_file = root / f"{kind}.html"
        html_file.write_text(render_html_source(doc, kind), encoding="utf-8")
        if browser is None and (data := _print_with_playwright(html_file)) is not None:
            return data
        exe = find_browser() if browser is None else None
        prefix = browser or ([str(exe)] if exe else None)
        if prefix is None:
            raise RenderError(
                "Aucun navigateur compatible trouvé pour le moteur HTML (Edge ou Chrome). "
                "Utilise le moteur Typst dans les réglages."
            )
        pdf_file = root / "out.pdf"
        command = browser_command(prefix, html_file, pdf_file, root / "profile")
        try:
            completed = subprocess.run(  # noqa: S603 - fixed arguments, no shell
                command, capture_output=True, timeout=BROWSER_TIMEOUT_SECONDS, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RenderError(
                "Le navigateur n'a pas pu produire le PDF.", detail=repr(exc)
            ) from exc
        if not pdf_file.is_file():
            stderr = completed.stderr.decode("utf-8", "replace")[-500:]
            raise RenderError("Le navigateur n'a pas pu produire le PDF.", detail=stderr)
        return pdf_file.read_bytes()
