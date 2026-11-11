"""The AI draft of an application and the prompts that produce it (SPEC 5.4, 7.1, 7.3, 7.4).

One call writes the whole application (CV selection, letter, e-mail, tips) to
save the user's quota. The AI only returns *references* (E0, P2...) and rewritten
bullets: facts are rebuilt from the library by honesty.py and assemble.py.

The draft model is lenient (every field has a default) because a missing part
must not reject the whole answer; honesty.py fills the gaps.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from postulo.services import prompts
from postulo.services.documents.model import DocLang
from postulo.services.documents.rules import rules_prompt
from postulo.services.documents.selection import MAX_INTERESTS, default_order, limits_for
from postulo.services.profile.references import assign_references
from postulo.services.profile.schema import CareerProfile
from postulo.services.prompts.sanitize import sanitize_text

MAX_OFFER_CHARS = 15_000


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _upper_ref(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


class DraftItem(_Lenient):
    ref: str
    bullets: list[str] = Field(default_factory=list)

    _norm = field_validator("ref", mode="before")(_upper_ref)


class DraftSkills(_Lenient):
    category: str = ""
    items: list[str] = Field(default_factory=list)


class DraftCv(_Lenient):
    title: str = ""
    summary: str = ""
    section_order: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experiences: list[DraftItem] = Field(default_factory=list)
    projects: list[DraftItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    volunteering: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    skills: list[DraftSkills] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)

    @field_validator(
        "education", "certifications", "awards", "volunteering", "publications", "languages",
        mode="before",
    )  # fmt: skip
    @classmethod
    def _refs(cls, value: object) -> object:
        if isinstance(value, list):
            return [_upper_ref(v) for v in value if isinstance(v, str)]
        return value


class DraftOffer(_Lenient):
    title: str = ""
    organization: str = ""
    keywords: list[str] = Field(default_factory=list)


class DraftLetter(_Lenient):
    subject: str = ""
    paragraphs: list[str] = Field(default_factory=list)


class DraftEmail(_Lenient):
    subject: str = ""
    body: str = ""


class ApplicationDraft(_Lenient):
    offer: DraftOffer = Field(default_factory=DraftOffer)
    cv: DraftCv = Field(default_factory=DraftCv)
    letter: DraftLetter = Field(default_factory=DraftLetter)
    email: DraftEmail = Field(default_factory=DraftEmail)
    tips: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


def merge_revision(original: ApplicationDraft, revised: ApplicationDraft) -> ApplicationDraft:
    """SPEC 7.6: keep the useful parts of the original draft the revision left out."""
    merged = original.model_copy(deep=True)
    for part in ("offer", "cv", "letter", "email"):
        target = getattr(merged, part)
        source = getattr(revised, part)
        for name in source.model_fields_set:
            value = getattr(source, name)
            if value not in ("", [], None):
                setattr(target, name, value)
    for name in ("tips", "gaps"):
        if value := getattr(revised, name):
            setattr(merged, name, value)
    return merged


# --- prompt context -----------------------------------------------------------------------------


def prompt_library(profile: CareerProfile) -> dict[str, Any]:
    """The library as the AI sees it: references, no internal ids, no contact details."""
    refs = {
        ref: item.model_dump(mode="json", exclude={"id"}, exclude_defaults=True)
        for ref, item in assign_references(profile).items()
    }
    return {
        "headline": profile.headline,
        "summary": profile.summary,
        "objective": profile.objective.model_dump(mode="json", exclude_defaults=True),
        "items": refs,
        "skills": [{"category": g.category, "items": g.items} for g in profile.skills if g.items],
        "interests": profile.interests,
        "extra_facts": profile.extra_facts,
    }


def _common_context(
    profile: CareerProfile, offer_text: str, lang: DocLang, position: str, organization: str
) -> dict[str, Any]:
    limits = limits_for(profile)
    return {
        "position": position,
        "organization": organization,
        "rules": rules_prompt(lang),
        "lang": lang,
        "lang_name": "français" if lang == "fr" else "anglais",
        "level": (profile.objective.level.value if profile.objective.level else "student"),
        "contract": (
            profile.objective.contract_type.value if profile.objective.contract_type else ""
        ),
        "limits": limits,
        "max_interests": MAX_INTERESTS,
        "default_order": ", ".join(default_order(profile)),
        "today": date.today().isoformat(),
        "library_json": json.dumps(prompt_library(profile), ensure_ascii=False, indent=1),
        "offer_text": offer_text,
    }


def sanitize_offer(offer_text: str) -> tuple[str, list[str]]:
    sanitized = sanitize_text(offer_text, max_chars=MAX_OFFER_CHARS)
    return sanitized.text, sanitized.warnings


def build_draft_prompt(
    profile: CareerProfile,
    offer_text: str,
    lang: DocLang,
    *,
    position: str,
    organization: str = "",
) -> str:
    """`offer_text` must already be sanitized (sanitize_offer)."""
    context = _common_context(profile, offer_text, lang, position, organization)
    return prompts.render("application_draft", **context)


def build_offer_meta_prompt(offer_text: str) -> str:
    """`offer_text` must already be sanitized (sanitize_offer)."""
    return prompts.render("offer_meta", offer_text=offer_text)


def build_revision_prompt(
    profile: CareerProfile,
    offer_text: str,
    lang: DocLang,
    draft: ApplicationDraft,
    critique: dict[str, Any],
    ats_report: dict[str, Any],
    *,
    position: str,
    organization: str = "",
) -> str:
    return prompts.render(
        "application_revision",
        **_common_context(profile, offer_text, lang, position, organization),
        draft_json=draft.model_dump_json(indent=1),
        critique_json=json.dumps(critique, ensure_ascii=False, indent=1),
        ats_json=json.dumps(ats_report, ensure_ascii=False, indent=1),
    )
