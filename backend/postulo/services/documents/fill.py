"""Fill a short one-page CV with relevant library content (docs/SPEC.md section 16.1).

A one-page CV should use 85 to 100 % of its page. Below 85 %, before touching the
spacing, the selection grows with content of the library that is relevant to the
offer (it shares at least one keyword with it), in this order:
1. an original bullet not yet used, for a selected experience or project;
2. a project, then an experience, not yet selected (within the selection limits);
3. a certification, an award or a volunteering not yet selected;
4. a skill category not yet shown.
An addition that pushes the CV past one page is skipped. Irrelevant content is never
added: a page filled at 85 % is better than a bullet unrelated to the position.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from postulo.services.documents.honesty import normalize_term, offer_tokens, tokens
from postulo.services.documents.model import CvDocument
from postulo.services.documents.render import RenderedPdf, fill_ratio
from postulo.services.documents.selection import (
    SelectedItem,
    Selection,
    SkillCategory,
    limits_for,
)
from postulo.services.profile.schema import CareerProfile, Experience, Project

MIN_FILL = 0.85
MAX_RENDERS = 10


@dataclass(frozen=True)
class FillResult:
    selection: Selection
    fill: float
    added: list[str]  # human-readable description of each addition


def _relevant(text: str, offer: set[str]) -> bool:
    return bool(tokens(text) & offer)


def _item_text(item: Experience | Project) -> str:
    name = item.title if isinstance(item, Experience) else item.name
    return " ".join([name, item.context, *item.achievements, *item.skills])


def _additions(
    selection: Selection, profile: CareerProfile, offer: set[str]
) -> Iterator[tuple[str, Selection]]:
    limits = limits_for(profile)

    # 1. Unused original bullets of the selected items.
    for field, items, per_item in (
        ("experiences", profile.experiences, limits.bullets_per_experience),
        ("projects", profile.projects, limits.bullets_per_project),
    ):
        chosen: list[SelectedItem] = getattr(selection, field)
        for position, item in enumerate(chosen):
            source = items[int(item.ref[1:])]
            if len(item.bullets) >= per_item:
                continue
            used = {normalize_term(b) for b in item.bullets}
            for bullet in source.achievements:
                if normalize_term(bullet) not in used and _relevant(bullet, offer):
                    grown = selection.model_copy(deep=True)
                    getattr(grown, field)[position].bullets.append(bullet)
                    yield f"bullet:{item.ref}:{normalize_term(bullet)[:40]}", grown
                    break

    # 2. Projects then experiences not selected yet.
    groups: list[tuple[str, str, list[Experience] | list[Project], int, int]] = [
        ("projects", "P", profile.projects, limits.projects, limits.bullets_per_project),
        ("experiences", "E", profile.experiences, limits.experiences,
         limits.bullets_per_experience),
    ]  # fmt: skip
    for field, prefix, items, limit, per_item in groups:
        chosen = getattr(selection, field)
        if len(chosen) >= limit:
            continue
        taken = {c.ref for c in chosen}
        candidates: list[Experience | Project] = list(items)
        for index, entry in enumerate(candidates):
            ref = f"{prefix}{index}"
            if ref not in taken and _relevant(_item_text(entry), offer):
                bullets = [b for b in entry.achievements if _relevant(b, offer)][:per_item]
                grown = selection.model_copy(deep=True)
                getattr(grown, field).append(SelectedItem(ref=ref, bullets=bullets))
                yield f"item:{ref}", grown
                break

    # 3. Certifications, awards, volunteering not selected yet.
    for field, prefix, entries in (
        ("certifications", "C", [(c.name, c.issuer) for c in profile.certifications]),
        ("awards", "R", [(a.title, a.description) for a in profile.awards]),
        ("volunteering", "A", [(v.role, v.description) for v in profile.volunteering]),
    ):
        taken = set(getattr(selection, field))
        for index, texts in enumerate(entries):
            ref = f"{prefix}{index}"
            if ref not in taken and _relevant(" ".join(texts), offer):
                grown = selection.model_copy(deep=True)
                getattr(grown, field).append(ref)
                yield f"item:{ref}", grown
                break

    # 4. A skill category not shown yet.
    if len(selection.skills) < limits.skill_categories:
        shown = {normalize_term(g.category) for g in selection.skills}
        for group in profile.skills:
            if normalize_term(group.category) in shown or not group.items:
                continue
            if _relevant(" ".join(group.items), offer):
                grown = selection.model_copy(deep=True)
                grown.skills.append(SkillCategory(category=group.category, items=list(group.items)))
                yield f"skills:{normalize_term(group.category)}", grown
                break


def fill_selection(
    selection: Selection,
    profile: CareerProfile,
    offer_text: str,
    *,
    build: Callable[[Selection], CvDocument],
    render: Callable[[CvDocument], RenderedPdf],
) -> FillResult:
    """Grow `selection` with relevant content until the one-page CV reaches 85 %."""
    current = selection.model_copy(deep=True)
    doc = build(current)
    rendered = render(doc)
    if rendered.pages > 1:
        return FillResult(current, 1.0, [])
    fill = fill_ratio(rendered.data, doc)
    offer = offer_tokens(offer_text)
    rejected: set[str] = set()
    added: list[str] = []
    renders = 1
    while fill < MIN_FILL and renders < MAX_RENDERS:
        progressed = False
        for key, candidate in _additions(current, profile, offer):
            if key in rejected:
                continue
            renders += 1
            candidate_doc = build(candidate)
            candidate_pdf = render(candidate_doc)
            if candidate_pdf.pages > 1:
                rejected.add(key)
            else:
                current, fill = candidate, fill_ratio(candidate_pdf.data, candidate_doc)
                added.append(key)
                progressed = True
                break
            if renders >= MAX_RENDERS:
                break
        if not progressed:
            break
    return FillResult(current, fill, added)
