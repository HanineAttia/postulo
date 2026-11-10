"""What goes on a CV: selected references, rewritten bullets and section order.

A `Selection` is the honest, validated form of the AI draft (see honesty.py):
it only contains references that exist in the library, skills and interests
that come from the library, and bullets checked against their source item.
`assemble.build_cv` turns it into a render-ready `CvDocument`.

Selection limits and default orders follow docs/SPEC.md section 7.1.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from postulo.services.documents.model import SECTION_KEYS
from postulo.services.profile.schema import CareerProfile, Level


@dataclass(frozen=True)
class Limits:
    experiences: int
    projects: int
    bullets_per_experience: int
    bullets_per_project: int
    skill_categories: int
    pages: int


_JUNIOR_LIKE = Limits(4, 2, 4, 2, 4, 1)
LIMITS: dict[Level, Limits] = {
    Level.STUDENT: Limits(3, 3, 3, 2, 4, 1),
    Level.RECENT_GRADUATE: Limits(3, 3, 3, 2, 4, 1),
    Level.JUNIOR: _JUNIOR_LIKE,
    Level.EXPERIENCED: Limits(5, 2, 4, 2, 5, 2),
    Level.SENIOR: Limits(5, 2, 4, 2, 5, 2),
}

STUDENT_ORDER = (
    "education", "experiences", "projects", "skills", "certifications",
    "languages", "awards", "volunteering", "publications", "interests",
)  # fmt: skip
EXPERIENCED_ORDER = (
    "experiences", "skills", "education", "certifications", "projects",
    "languages", "publications", "awards", "volunteering", "interests",
)  # fmt: skip
assert set(STUDENT_ORDER) == set(EXPERIENCED_ORDER) == set(SECTION_KEYS)

MAX_INTERESTS = 3


def profile_level(profile: CareerProfile) -> Level:
    return profile.objective.level or Level.STUDENT


def limits_for(profile: CareerProfile) -> Limits:
    return LIMITS[profile_level(profile)]


def default_order(profile: CareerProfile) -> tuple[str, ...]:
    """SPEC 7.1: students put education first, unless they have 3+ experiences."""
    level = profile_level(profile)
    if level in (Level.STUDENT, Level.RECENT_GRADUATE):
        if len(profile.experiences) >= 3:
            return ("experiences", "education", *STUDENT_ORDER[2:])
        return STUDENT_ORDER
    if level == Level.JUNIOR:
        return ("experiences", "education", "projects", "skills", *STUDENT_ORDER[4:])
    return EXPERIENCED_ORDER


def complete_order(proposed: list[str], profile: CareerProfile) -> list[str]:
    """Keep the valid, unique keys proposed by the AI, then add the missing ones."""
    order: list[str] = []
    for key in proposed:
        if key in SECTION_KEYS and key not in order:
            order.append(key)
    order.extend(key for key in default_order(profile) if key not in order)
    return order


class SelectedItem(BaseModel):
    ref: str
    bullets: list[str] = Field(default_factory=list)


class SkillCategory(BaseModel):
    category: str
    items: list[str] = Field(default_factory=list)


class Selection(BaseModel):
    title: str = ""
    summary: str = ""
    section_order: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experiences: list[SelectedItem] = Field(default_factory=list)
    projects: list[SelectedItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    volunteering: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    skills: list[SkillCategory] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


def default_selection(profile: CareerProfile) -> Selection:
    """A selection without AI: library order, original bullets, within the limits."""
    limits = limits_for(profile)
    return Selection(
        title=profile.headline,
        summary=profile.summary,
        section_order=list(default_order(profile)),
        education=[f"F{i}" for i in range(len(profile.education))],
        experiences=[
            SelectedItem(ref=f"E{i}", bullets=e.achievements[: limits.bullets_per_experience])
            for i, e in enumerate(profile.experiences[: limits.experiences])
        ],
        projects=[
            SelectedItem(ref=f"P{i}", bullets=p.achievements[: limits.bullets_per_project])
            for i, p in enumerate(profile.projects[: limits.projects])
        ],
        certifications=[f"C{i}" for i in range(len(profile.certifications))],
        awards=[f"R{i}" for i in range(len(profile.awards))],
        volunteering=[f"A{i}" for i in range(len(profile.volunteering))],
        publications=[f"U{i}" for i in range(len(profile.publications))],
        languages=[f"L{i}" for i in range(len(profile.languages))],
        skills=[
            SkillCategory(category=g.category, items=list(g.items))
            for g in profile.skills[: limits.skill_categories]
            if g.items
        ],
        interests=profile.interests[:MAX_INTERESTS],
    )
