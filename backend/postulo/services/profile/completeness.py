"""Completeness score (0-100) and concrete advice (docs/SPEC.md section 6.2).

Each check is worth a number of points; a failed check yields an advice whose
`key` the frontend translates (with `params`). Advice is sorted by points lost.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from postulo.services.profile.schema import CareerProfile

_NUMBER_RE = re.compile(r"\d")


class Advice(BaseModel):
    key: str
    section: str  # tab of the "Mon parcours" page that fixes it
    points: int
    params: dict[str, int | str] = {}


class Completeness(BaseModel):
    score: int
    advice: list[Advice]


@dataclass(frozen=True)
class _Check:
    key: str
    section: str
    points: int
    # Returns the earned fraction (0..1) and optional params for the advice.
    evaluate: _Evaluator


_Evaluator = Callable[[CareerProfile], tuple[float, dict[str, int | str]]]


def _bool(predicate: Callable[[CareerProfile], bool]) -> _Evaluator:
    return lambda p: (1.0 if predicate(p) else 0.0, {})


def _all_achievements(p: CareerProfile) -> list[str]:
    lines = [a for e in p.experiences for a in e.achievements]
    return lines + [a for pr in p.projects for a in pr.achievements]


def _quantified(p: CareerProfile) -> tuple[float, dict[str, int | str]]:
    lines = _all_achievements(p)
    if not lines:
        return 0.0, {"count": 0, "total": 0}
    count = sum(1 for line in lines if _NUMBER_RE.search(line))
    # Half of the achievements with a figure is a good target.
    return min(1.0, count / max(1, len(lines) / 2)), {"count": count, "total": len(lines)}


def _projects(p: CareerProfile) -> tuple[float, dict[str, int | str]]:
    return min(1.0, len(p.projects) / 2), {"count": len(p.projects)}


def _achievements_per_experience(p: CareerProfile) -> tuple[float, dict[str, int | str]]:
    if not p.experiences:
        return 0.0, {"count": 0}
    weak = sum(1 for e in p.experiences if len(e.achievements) < 2)
    return 1.0 - weak / len(p.experiences), {"count": weak}


def _skills(p: CareerProfile) -> tuple[float, dict[str, int | str]]:
    items = sum(len(group.items) for group in p.skills)
    return min(1.0, items / 6), {"count": items}


CHECKS: tuple[_Check, ...] = (
    _Check(
        "name", "identity", 8, _bool(lambda p: bool(p.identity.first_name and p.identity.last_name))
    ),
    _Check("email", "identity", 5, _bool(lambda p: bool(p.identity.email))),
    _Check("phone", "identity", 3, _bool(lambda p: bool(p.identity.phone))),
    _Check("city", "identity", 3, _bool(lambda p: bool(p.identity.city))),
    _Check("linkedin", "identity", 4, _bool(lambda p: bool(p.identity.linkedin))),
    _Check(
        "portfolio",
        "identity",
        3,
        _bool(lambda p: bool(p.identity.github or p.identity.portfolio or p.identity.links)),
    ),
    _Check("headline", "identity", 4, _bool(lambda p: bool(p.headline))),
    _Check("summary", "identity", 5, _bool(lambda p: bool(p.summary))),
    _Check("contract_type", "objective", 4, _bool(lambda p: p.objective.contract_type is not None)),
    _Check("target_roles", "objective", 5, _bool(lambda p: bool(p.objective.target_roles))),
    _Check("availability", "objective", 3, _bool(lambda p: bool(p.objective.availability))),
    _Check("zones", "objective", 2, _bool(lambda p: bool(p.objective.zones))),
    _Check("level", "objective", 2, _bool(lambda p: p.objective.level is not None)),
    _Check("education", "education", 8, _bool(lambda p: bool(p.education))),
    _Check("experiences", "experiences", 8, _bool(lambda p: bool(p.experiences))),
    _Check("quantified", "experiences", 10, _quantified),
    _Check("achievements", "experiences", 4, _achievements_per_experience),
    _Check("projects", "projects", 8, _projects),
    _Check("skills", "skills", 6, _skills),
    _Check("languages", "skills", 5, _bool(lambda p: bool(p.languages))),
)
assert sum(check.points for check in CHECKS) == 100


def compute_completeness(profile: CareerProfile) -> Completeness:
    score = 0.0
    advice: list[Advice] = []
    for check in CHECKS:
        fraction, params = check.evaluate(profile)
        earned = check.points * max(0.0, min(1.0, fraction))
        score += earned
        lost = round(check.points - earned)
        if lost > 0:
            advice.append(Advice(key=check.key, section=check.section, points=lost, params=params))
    advice.sort(key=lambda a: a.points, reverse=True)
    return Completeness(score=round(score), advice=advice)
