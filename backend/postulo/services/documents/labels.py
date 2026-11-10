"""Printed labels of the documents, in French and English (SPEC 7.1 and 7.2).

These are document strings, not UI strings: they end up in the PDF, in the
language chosen for the application, not in the interface language.
"""

from __future__ import annotations

from postulo.services.documents.model import DocLang

_MONTHS: dict[DocLang, tuple[str, ...]] = {
    "fr": ("janv.", "févr.", "mars", "avr.", "mai", "juin",
           "juil.", "août", "sept.", "oct.", "nov.", "déc."),
    "en": ("Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.",
           "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."),
}  # fmt: skip
_LONG_MONTHS_FR = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                   "septembre", "octobre", "novembre", "décembre")  # fmt: skip
_LONG_MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August",
                   "September", "October", "November", "December")  # fmt: skip

ONGOING: dict[DocLang, str] = {"fr": "aujourd'hui", "en": "Present"}

# Standard headings understood by ATS (SPEC 7.2). Normal case, never uppercased.
SECTION_TITLES: dict[DocLang, dict[str, str]] = {
    "fr": {
        "education": "Formation",
        "experiences": "Expérience professionnelle",
        "projects": "Projets",
        "skills": "Compétences",
        "certifications": "Certifications",
        "languages": "Langues",
        "awards": "Prix et distinctions",
        "volunteering": "Engagements",
        "publications": "Publications",
        "interests": "Centres d'intérêt",
    },
    "en": {
        "education": "Education",
        "experiences": "Experience",
        "projects": "Projects",
        "skills": "Skills",
        "certifications": "Certifications",
        "languages": "Languages",
        "awards": "Awards",
        "volunteering": "Volunteering",
        "publications": "Publications",
        "interests": "Interests",
    },
}

LANGUAGE_LEVELS: dict[DocLang, dict[str, str]] = {
    "fr": {
        "native": "langue maternelle",
        "bilingual": "bilingue",
        "c1_c2": "courant (C1-C2)",
        "b2": "B2",
        "b1": "B1",
        "a1_a2": "notions (A1-A2)",
    },
    "en": {
        "native": "native",
        "bilingual": "bilingual",
        "c1_c2": "fluent (C1-C2)",
        "b2": "B2",
        "b1": "B1",
        "a1_a2": "basic (A1-A2)",
    },
}

KEY_COURSES: dict[DocLang, str] = {"fr": "Cours clés : ", "en": "Key courses: "}


def format_month(value: str | None, lang: DocLang) -> str:
    """'2024-09' -> 'sept. 2024' / 'Sep. 2024'; '2024' -> '2024'; None -> ''."""
    if not value:
        return ""
    year, _, month = value.partition("-")
    if not month:
        return year
    return f"{_MONTHS[lang][int(month) - 1]} {year}"


def format_range(start: str | None, end: str | None, lang: DocLang, *, ongoing: bool) -> str:
    """Single date format of SPEC 7.1: 'sept. 2024 – juin 2026', 'aujourd'hui' if ongoing.

    `ongoing` tells whether an empty `end` means "still running" (experiences) or
    simply "unknown" (a project without dates).
    """
    first = format_month(start, lang)
    last = format_month(end, lang) if end else (ONGOING[lang] if ongoing and start else "")
    if first and last and first != last:
        return f"{first} – {last}"
    return first or last


def long_date(year: int, month: int, day: int, lang: DocLang) -> str:
    if lang == "fr":
        day_text = "1er" if day == 1 else str(day)
        return f"{day_text} {_LONG_MONTHS_FR[month - 1]} {year}"
    return f"{_LONG_MONTHS_EN[month - 1]} {day}, {year}"
