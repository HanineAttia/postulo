"""Automatic ATS check of a generated CV (docs/SPEC.md section 7.6).

Text is extracted with pypdfium2 (pypdf sometimes splits words, lesson 3), links
with pypdf (`/URI` annotations). Score: 60 % for the checks, 40 % for the
coverage of the offer keywords (or 100 % checks when there are no keywords).
Check labels are translated by the frontend from their `key`; `detail` is a
short French explanation.
"""

from __future__ import annotations

import io
import re

import pypdfium2 as pdfium
from pydantic import BaseModel, Field
from pypdf import PdfReader

from postulo.services.documents.honesty import contains_term, normalize_term
from postulo.services.profile.schema import CareerProfile

MIN_TEXT_CHARS = 400
CHECKS_WEIGHT = 0.6
# U+FFFD replacement char, U+25A1 white square (missing glyph), U+F0B7 private-use bullet.
_BAD_CHARS = ("�", "□", "")
_LIGATURES_RE = re.compile("[ﬀ-ﬆ]")
_DATE_RE = re.compile(
    r"\b(?:janv|févr|fevr|mars|avr|mai|juin|juil|août|aout|sept|oct|nov|déc|dec|jan|feb|mar|apr|"
    r"may|jun|jul|aug|sep)[a-zéû]*\.?\s+(?:19|20)\d{2}\b|\b(?:19|20)\d{2}\s*[–-]\s*(?:(?:19|20)\d{2}|"
    r"aujourd'hui|present)",
    re.IGNORECASE,
)


class AtsCheckResult(BaseModel):
    key: str
    ok: bool
    detail: str = ""


class AtsReport(BaseModel):
    score: int
    checks_score: int
    coverage: int | None
    checks: list[AtsCheckResult]
    keywords_found: list[str] = Field(default_factory=list)
    keywords_missing: list[str] = Field(default_factory=list)
    pages: int
    text: str
    links: list[str] = Field(default_factory=list)

    def summary_for_prompt(self) -> dict[str, object]:
        """What the revision prompt needs (no full text: the AI already has the draft)."""
        return {
            "score": self.score,
            "failed_checks": [c.key for c in self.checks if not c.ok],
            "keywords_found": self.keywords_found,
            "keywords_missing": self.keywords_missing,
        }


def extract_text(pdf: bytes) -> tuple[str, int]:
    """Text as an ATS sees it, and the page count."""
    document = pdfium.PdfDocument(pdf)
    try:
        pages: list[str] = []
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_range())
            textpage.close()
            page.close()
        count = len(document)
    finally:
        document.close()
    # pdfium marks a hyphen at the end of a line with U+FFFE: it is a real hyphen.
    text = "\n".join(pages).replace("\r\n", "\n").replace("\r", "\n").replace("￾", "-")
    return text, count


def extract_links(pdf: bytes) -> list[str]:
    links: list[str] = []
    for page in PdfReader(io.BytesIO(pdf)).pages:
        for annotation in page.get("/Annots", None) or []:
            action = annotation.get_object().get("/A")
            if action is not None and "/URI" in action:
                links.append(str(action["/URI"]))
    return links


def _same_url(a: str, b: str) -> bool:
    def key(url: str) -> str:
        url = re.sub(r"^https?://(www\.)?", "", url.strip().lower())
        return url.rstrip("/")

    return key(a) == key(b)


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def check_cv_pdf(
    pdf: bytes,
    *,
    profile: CareerProfile,
    keywords: list[str],
    target_pages: int,
    headings: list[str],
) -> AtsReport:
    text, pages = extract_text(pdf)
    links = extract_links(pdf)
    ident = profile.identity
    name = " ".join(p for p in (ident.first_name, ident.last_name) if p)
    flat = " ".join(text.split())
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    checks: list[AtsCheckResult] = []

    def add(key: str, ok: bool, detail: str = "") -> None:
        checks.append(AtsCheckResult(key=key, ok=ok, detail="" if ok else detail))

    chars = len(re.sub(r"\s", "", text))
    add("text_extractable", chars > MIN_TEXT_CHARS, f"Seulement {chars} caractères lisibles.")
    add("page_count", pages <= target_pages, f"{pages} pages pour un objectif de {target_pages}.")
    add(
        "name_first_line",
        bool(lines) and bool(name) and lines[0].casefold() == name.casefold(),
        "Le nom n'est pas sur la première ligne du texte extrait.",
    )
    if ident.email:
        add("email_readable", ident.email in flat, "L'e-mail n'est pas lisible dans le texte.")
    if ident.phone:
        add(
            "phone_readable",
            _digits(ident.phone) in _digits(flat),
            "Le téléphone n'est pas lisible dans le texte.",
        )
    expected = [f"mailto:{ident.email}"] if ident.email else []
    expected += [u for u in (ident.linkedin, ident.github, ident.portfolio) if u]
    missing_links = [u for u in expected if not any(_same_url(u, link) for link in links)]
    add(
        "links_clickable",
        not missing_links,
        "Liens non cliquables : " + ", ".join(missing_links) + ".",
    )
    missing_headings = [h for h in headings if h not in lines]
    add(
        "standard_headings",
        bool(headings) and not missing_headings,
        "Intitulés introuvables : " + ", ".join(missing_headings) + ".",
    )
    bad = sorted({f"U+{ord(c):04X}" for c in _BAD_CHARS if c in text})
    add("no_bad_characters", not bad, "Caractères illisibles : " + ", ".join(bad) + ".")
    ligatures = sorted({f"U+{ord(c):04X}" for c in _LIGATURES_RE.findall(text)})
    add("no_ligatures", not ligatures, "Ligatures trouvées : " + ", ".join(ligatures) + ".")
    add("dates_detected", len(_DATE_RE.findall(flat)) >= 1, "Aucune date reconnue.")

    checks_score = round(100 * sum(c.ok for c in checks) / len(checks))
    normalized = normalize_term(flat)
    found = [k for k in keywords if contains_term(normalized, k)]
    missing = [k for k in keywords if k not in found]
    coverage = round(100 * len(found) / len(keywords)) if keywords else None
    if coverage is None:
        score = checks_score
    else:
        score = round(CHECKS_WEIGHT * checks_score + (1 - CHECKS_WEIGHT) * coverage)
    return AtsReport(
        score=score,
        checks_score=checks_score,
        coverage=coverage,
        checks=checks,
        keywords_found=found,
        keywords_missing=missing,
        pages=pages,
        text=text,
        links=links,
    )
