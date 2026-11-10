"""Stable short references for prompts (docs/SPEC.md section 6.1).

F = formation (education), E = experiences, P = projects, C = certifications,
R = récompenses (awards), A = engagements associatifs (volunteering),
U = publications, L = languages. They are recomputed for every generation from
the current order of the lists, and never stored.
"""

from __future__ import annotations

from pydantic import BaseModel

from postulo.services.profile.schema import CareerProfile

PREFIXES: dict[str, str] = {
    "education": "F",
    "experiences": "E",
    "projects": "P",
    "certifications": "C",
    "awards": "R",
    "volunteering": "A",
    "publications": "U",
    "languages": "L",
}


def assign_references(profile: CareerProfile) -> dict[str, BaseModel]:
    """Return {"E0": experience, "E1": ..., "P0": project, ...} in display order."""
    refs: dict[str, BaseModel] = {}
    for section, prefix in PREFIXES.items():
        items: list[BaseModel] = getattr(profile, section)
        for index, item in enumerate(items):
            refs[f"{prefix}{index}"] = item
    return refs
