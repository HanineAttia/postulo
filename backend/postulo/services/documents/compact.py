"""Fit the CV to its target page count (SPEC 7.5, 16.1, lesson 8).

Compaction levels, when the CV is too long (each includes the previous ones):
0. normal;
1. smaller margins and spacing;
2. smaller font (never below 9.2 pt);
3. no interests, publications nor volunteering; at most 2 bullets per item;
4. no awards; at most 2 projects and 3 experiences.

Airy steps, when a one-page CV fills less than 85 % of its page (SPEC 16.1): the
spacing grows a little, without ever going past one page. Content is added
before that, by fill.py, and only if it is relevant to the offer.

Each level is applied to a deep copy of the full document: the full version is
the one the user edits, so a regeneration can always start again from level 0.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from postulo.services.documents.model import CvDocument, LetterDocument
from postulo.services.documents.render import RenderedPdf, fill_ratio

MAX_LEVEL = 4
MAX_AIRY = 2
MIN_FONT_SIZE = 9.2
MIN_FILL = 0.85

_LAYOUTS: dict[int, dict[str, float]] = {
    1: {"margin_x": 13.0, "margin_y": 11.0, "leading": 0.44, "section_gap": 8.0,
        "entry_gap": 4.0, "bullet_gap": 1.5},
    2: {"margin_x": 11.0, "margin_y": 9.0, "leading": 0.4, "section_gap": 7.0,
        "entry_gap": 3.5, "bullet_gap": 1.0, "size": 9.4},
}  # fmt: skip
_AIRY: dict[int, dict[str, float]] = {
    1: {"leading": 0.56, "section_gap": 12.0, "entry_gap": 6.5, "bullet_gap": 2.5},
    2: {"leading": 0.62, "section_gap": 14.0, "entry_gap": 8.0, "bullet_gap": 3.0,
        "size": 10.5},
}  # fmt: skip
_LEVEL3_DROPPED = ("interests", "publications", "volunteering")
_LEVEL4_DROPPED = ("awards",)
_LEVEL4_MAX_ENTRIES = {"projects": 2, "experiences": 3}


def _layout_changes(level: int) -> dict[str, Any]:
    changes: dict[str, Any] = {"level": level, "airy": 0}
    for step in range(1, min(level, 2) + 1):
        changes.update(_LAYOUTS[step])
    if "size" in changes:
        changes["size"] = max(MIN_FONT_SIZE, changes["size"])
    return changes


def apply_level(doc: CvDocument, level: int) -> CvDocument:
    """Return a compacted copy of `doc` (the original is never modified)."""
    out = doc.model_copy(deep=True)
    out.layout = out.layout.model_copy(update=_layout_changes(level))
    if level >= 3:
        dropped = _LEVEL3_DROPPED + (_LEVEL4_DROPPED if level >= 4 else ())
        out.sections = [s for s in out.sections if s.key not in dropped]
        for section in out.sections:
            for entry in section.entries:
                entry.bullets = entry.bullets[:2]
    if level >= 4:
        for section in out.sections:
            limit = _LEVEL4_MAX_ENTRIES.get(section.key)
            if limit is not None:
                section.entries = section.entries[:limit]
    return out


def apply_airy(doc: CvDocument, step: int) -> CvDocument:
    """Return a copy of `doc` with more generous spacing (step 1 or 2)."""
    out = doc.model_copy(deep=True)
    out.layout = out.layout.model_copy(update={**_AIRY[step], "level": 0, "airy": step})
    return out


def compact_cv(
    doc: CvDocument, target_pages: int, render: Callable[[CvDocument], RenderedPdf]
) -> tuple[CvDocument, RenderedPdf]:
    """Render level by level until it fits; on a short one-page CV, air it out a little.

    Returns the last attempt if nothing fits.
    """
    attempt = apply_level(doc, 0)
    rendered = render(attempt)
    level = 0
    while rendered.pages > target_pages and level < MAX_LEVEL:
        level += 1
        attempt = apply_level(doc, level)
        rendered = render(attempt)
    if level == 0 and target_pages == 1 and fill_ratio(rendered.data, attempt) < MIN_FILL:
        for step in range(1, MAX_AIRY + 1):
            airy = apply_airy(doc, step)
            candidate = render(airy)
            if candidate.pages > 1:
                break
            attempt, rendered = airy, candidate
            if fill_ratio(rendered.data, attempt) >= MIN_FILL:
                break
    return attempt, rendered


def compact_letter(
    doc: LetterDocument, render: Callable[[LetterDocument], RenderedPdf]
) -> tuple[LetterDocument, RenderedPdf]:
    """A letter always fits one page: only the font size can be reduced (margins are fixed)."""
    attempt = doc.model_copy(deep=True)
    rendered = render(attempt)
    level = 0
    while rendered.pages > 1 and level < 2:
        level += 1
        attempt = doc.model_copy(deep=True)
        attempt.layout = attempt.layout.model_copy(update=_layout_changes(level))
        rendered = render(attempt)
    return attempt, rendered
