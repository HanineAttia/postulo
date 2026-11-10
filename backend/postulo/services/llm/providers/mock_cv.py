"""Deterministic `cv_extract` answer for the MockProvider (tests and demo mode).

A tiny rule-based reader, no AI: it only understands simple, well-formed CVs:
name on the first line, headline on the second, then sections ("Expériences",
"Formation", "Projets", "Compétences", "Langues") with entries such as
"Titre — Organisation (2024-09 – 2025-06)" followed by "- réalisation" lines.
"""

from __future__ import annotations

import json
import re
from typing import Any

from postulo.services.profile.schema import strip_accents

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.]?)?(?:\(?0\)?[\s.]?)?\d(?:[\s.-]?\d{2}){4}")
_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?(linkedin\.com/in/[\w-]+|github\.com/[\w-]+)")
_DATES_RE = re.compile(r"\(([^)]*)\)\s*$")
_RANGE_SPLIT_RE = re.compile(r"\s+[–-]\s+|\s+à\s+")
_HEADINGS = {
    "experiences": ("experience", "experiences", "experiences professionnelles",
                    "experience professionnelle"),
    "education": ("formation", "formations", "education"),
    "projects": ("projet", "projets", "projects"),
    "skills": ("competences", "competence", "skills"),
    "languages": ("langues", "languages"),
}  # fmt: skip


def mock_cv_extract(prompt: str) -> str:
    # The CV is the last <cv> block (the instructions above also mention the tags).
    start = prompt.rfind("<cv>")
    end = prompt.rfind("</cv>")
    text = prompt[start + len("<cv>") : end] if 0 <= start < end else ""
    return "```json\n" + json.dumps(parse_simple_cv(text), ensure_ascii=False) + "\n```"


def _heading(line: str) -> str | None:
    key = strip_accents(line).lower().strip(" :")
    return next((name for name, words in _HEADINGS.items() if key in words), None)


def _split_entry(line: str) -> tuple[list[str], str | None, str | None]:
    start = end = None
    if dates := _DATES_RE.search(line):
        parts = _RANGE_SPLIT_RE.split(dates.group(1).strip())
        start = parts[0].strip() or None
        end = parts[1].strip() if len(parts) > 1 else None
        line = line[: dates.start()]
    fields = [part.strip() for part in re.split(r"\s+[—|]\s+|\s+-\s+", line) if part.strip()]
    return fields, start, end


def parse_simple_cv(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result: dict[str, Any] = {
        "identity": {},
        "experiences": [],
        "education": [],
        "projects": [],
        "skills": [],
        "languages": [],
    }
    if lines:
        first, _, last = lines[0].partition(" ")
        result["identity"].update(first_name=first, last_name=last)
    if len(lines) > 1 and _heading(lines[1]) is None and not _EMAIL_RE.search(lines[1]):
        result["headline"] = lines[1]
    if email := _EMAIL_RE.search(text):
        result["identity"]["email"] = email.group(0)
    if phone := _PHONE_RE.search(text):
        result["identity"]["phone"] = phone.group(0)
    for url in _URL_RE.findall(text):
        key = "linkedin" if url.startswith("linkedin") else "github"
        result["identity"][key] = "https://" + url

    section: str | None = None
    for line in lines[1:]:
        if (heading := _heading(line)) is not None:
            section = heading
            continue
        if section is None:
            continue
        if line.startswith(("- ", "• ", "* ")):
            items = result[section]
            if items and section in ("experiences", "projects"):
                items[-1]["achievements"].append(line[2:].strip())
            continue
        if section == "skills":
            category, _, values = line.partition(":")
            items_list = [v.strip() for v in values.split(",") if v.strip()]
            result["skills"].append({"category": category.strip(), "items": items_list})
        elif section == "languages":
            name, _, rest = line.partition(":")
            result["languages"].append({"name": name.strip(), "certificate": rest.strip()})
        else:
            fields, start, end = _split_entry(line)
            first_field = fields[0] if fields else line
            second = fields[1] if len(fields) > 1 else ""
            if section == "experiences":
                result["experiences"].append(
                    {"title": first_field, "organization": second, "start": start, "end": end,
                     "achievements": []}
                )  # fmt: skip
            elif section == "education":
                result["education"].append(
                    {"degree": first_field, "school": second, "start": start, "end": end}
                )
            else:
                result["projects"].append(
                    {"name": first_field, "start": start, "end": end, "achievements": []}
                )
    return result
