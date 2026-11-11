"""Automatic layout check of a generated CV (docs/SPEC.md section 16.1).

Uses the positions of the extracted text (pypdfium2), so it checks what is really
printed, whatever the engine:
- page fill rate (vertical position of the last text);
- every date on the same line as its title, on the right;
- no experience or education entry without organization nor date;
- no line of the body entirely in capitals;
- no bullet longer than 2 lines;
- no sentence fragment (a bullet ending with "de", "et", "à", "of"...).
"""

from __future__ import annotations

import re

import pypdfium2 as pdfium
from pydantic import BaseModel, Field

from postulo.services.documents.model import CvDocument
from postulo.services.documents.render import fill_ratio
from postulo.services.quality.ats_check import AtsCheckResult

MIN_FILL = 0.85
SAME_LINE_TOLERANCE = 0.45  # in em: two baselines closer than this are on the same line

FRAGMENT_ENDINGS = frozenset(
    re.findall(
        r"\S+",
        "de du des d' et à au aux en le la les l' un une pour avec par sur dans sans ou que qui "
        "of and the to for with a an in on by or from at",
    )
)
_WORD_END_RE = re.compile(r"([A-Za-zÀ-ÿ']+)\W*$")


class LayoutReport(BaseModel):
    fill: float  # share of the usable page height, last page
    checks: list[AtsCheckResult] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)


def is_fragment(text: str) -> bool:
    """A text that stops in the middle of a sentence ("... avec un pipeline de")."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith((",", ":", ";", "-", "–")):
        return True
    match = _WORD_END_RE.search(stripped)
    return match is not None and match.group(1).lower() in FRAGMENT_ENDINGS


Box = tuple[float, float, float, float]  # left, bottom, right, top (PDF points)


class _Page:
    """Search helper on the text layer of one PDF page (searches cross line breaks)."""

    def __init__(self, page: pdfium.PdfPage) -> None:
        self.textpage = page.get_textpage()

    def find(self, text: str) -> list[tuple[Box, Box]]:
        """(first character box, last character box) of every occurrence of `text`."""
        probe = text.strip()
        if not probe:
            return []
        hits: list[tuple[Box, Box]] = []
        searcher = self.textpage.search(probe, match_case=True)
        while (hit := searcher.get_next()) is not None:
            index, count = hit
            hits.append(
                (
                    self.textpage.get_charbox(index, loose=True),
                    self.textpage.get_charbox(index + count - 1, loose=True),
                )
            )
        searcher.close()
        return hits

    def close(self) -> None:
        self.textpage.close()


def check_layout(pdf: bytes, doc: CvDocument, *, target_pages: int = 1) -> LayoutReport:
    fill = fill_ratio(pdf, doc)
    checks: list[AtsCheckResult] = []

    def add(key: str, ok: bool, detail: str = "") -> None:
        checks.append(AtsCheckResult(key=key, ok=ok, detail="" if ok else detail))

    if target_pages == 1:
        add(
            "page_fill",
            MIN_FILL <= fill <= 1.0 + 1e-6,
            f"Page remplie à {round(fill * 100)} % (objectif : 85 à 100 %).",
        )

    em = doc.layout.size
    # Baseline to baseline: cap height (about 0.73 em with the bundled fonts) + leading.
    pitch = em * (0.73 + doc.layout.leading)
    document = pdfium.PdfDocument(pdf)
    pages = [_Page(document[i]) for i in range(len(document))]
    try:
        misplaced: list[str] = []
        long_bullets: list[str] = []
        for section in doc.sections:
            for entry in section.entries:
                if entry.dates and not _date_on_title_line(pages, entry.title, entry.dates, em):
                    misplaced.append(entry.title)
                for bullet in entry.bullets:
                    if _lines_of(pages, bullet, pitch) > 2:
                        long_bullets.append(bullet[:60])
        add(
            "dates_on_title_line",
            not misplaced,
            "Dates hors de la ligne de l'intitulé : " + "; ".join(misplaced) + ".",
        )
        add(
            "bullets_max_two_lines",
            not long_bullets,
            "Puces de plus de 2 lignes : " + "; ".join(long_bullets) + ".",
        )
    finally:
        for page in pages:
            page.close()
        document.close()

    incomplete = [
        e.title
        for s in doc.sections
        if s.key in ("experiences", "education")
        for e in s.entries
        if not e.subtitle and not e.dates
    ]
    add(
        "entries_complete",
        not incomplete,
        "Éléments sans organisation ni date : " + "; ".join(incomplete) + ".",
    )

    body = [doc.summary, *(e.title for s in doc.sections for e in s.entries)]
    body += [b for s in doc.sections for e in s.entries for b in e.bullets]
    shouting = [t for t in body if _all_caps(t)]
    add(
        "no_uppercase_lines",
        not shouting,
        "Lignes entièrement en majuscules : " + "; ".join(shouting) + ".",
    )

    fragments = [b for s in doc.sections for e in s.entries for b in e.bullets if is_fragment(b)]
    add(
        "no_fragments",
        not fragments,
        "Puces coupées au milieu d'une phrase : " + "; ".join(f[-50:] for f in fragments) + ".",
    )
    return LayoutReport(fill=round(fill, 3), checks=checks)


def _all_caps(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 4 and all(c.isupper() for c in letters)


def _date_on_title_line(pages: list[_Page], title: str, dates: str, em: float) -> bool:
    """True when the dates sit on the first line of the title, to its right."""
    for page in pages:
        for t_first, _t_last in page.find(title):
            for d_first, _d_last in page.find(dates):
                same_line = abs(t_first[1] - d_first[1]) <= SAME_LINE_TOLERANCE * em
                if same_line and d_first[0] > t_first[0]:
                    return True
    return False


def _lines_of(pages: list[_Page], text: str, pitch: float) -> int:
    """Number of lines a text spans: vertical distance between its first and last characters."""
    for page in pages:
        for first, last in page.find(text):
            return 1 + round((first[1] - last[1]) / pitch)
    return 1
