"""Automatic compaction until the CV fits the target page count (SPEC 7.5, lesson 8).

Levels (each includes the previous ones):
0. normal;
1. smaller margins and spacing;
2. smaller font (never below 9.2 pt);
3. no interests, publications nor volunteering; at most 2 bullets per item;
4. no awards; at most 2 projects and 3 experiences.

Each level is applied to a deep copy of the full document: the full version is
the one the user edits, so a regeneration can always start again from level 0.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from postulo.services.documents.model import CvDocument, LetterDocument
from postulo.services.documents.render import RenderedPdf

MAX_LEVEL = 4
MIN_FONT_SIZE = 9.2

_LAYOUTS: dict[int, dict[str, float]] = {
    1: {"margin_x": 11.0, "margin_y": 9.0, "leading": 0.5, "gap": 2.4, "item_gap": 1.1},
    2: {"margin_x": 10.0, "margin_y": 8.0, "leading": 0.46, "gap": 2.0, "item_gap": 0.9,
        "size": 9.3},
}  # fmt: skip
_LEVEL3_DROPPED = ("interests", "publications", "volunteering")
_LEVEL4_DROPPED = ("awards",)
_LEVEL4_MAX_ENTRIES = {"projects": 2, "experiences": 3}


def _layout_changes(level: int) -> dict[str, Any]:
    changes: dict[str, Any] = {"level": level}
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


def compact_cv(
    doc: CvDocument, target_pages: int, render: Callable[[CvDocument], RenderedPdf]
) -> tuple[CvDocument, RenderedPdf]:
    """Render level by level until it fits; return the last attempt if nothing fits."""
    attempt = apply_level(doc, 0)
    rendered = render(attempt)
    level = 0
    while rendered.pages > target_pages and level < MAX_LEVEL:
        level += 1
        attempt = apply_level(doc, level)
        rendered = render(attempt)
    return attempt, rendered


def compact_letter(
    doc: LetterDocument, render: Callable[[LetterDocument], RenderedPdf]
) -> tuple[LetterDocument, RenderedPdf]:
    """A letter always fits one page: only the layout levels (1 and 2) are used."""
    attempt = doc.model_copy(deep=True)
    rendered = render(attempt)
    level = 0
    while rendered.pages > 1 and level < 2:
        level += 1
        attempt = doc.model_copy(deep=True)
        attempt.layout = attempt.layout.model_copy(update=_layout_changes(level))
        rendered = render(attempt)
    return attempt, rendered
