"""Position, organization and city of an offer (docs/SPEC.md section 16.2).

Rules first (free, offline): labelled lines ("Poste :", "Entreprise :", "Lieu :"),
then the first line that contains a job word. A slogan or a catchphrase ("Construisons
ensemble un avenir de confiance") is never taken as the position: a line needs a job
word (stage, ingénieur, data scientist, H/F...). Slogan hints ("ensemble", "avenir",
"-ons", "!") are only hints: they never reject a line that has a job word.

The AI may then confirm or complete the result (`offer_meta` prompt); its position is
accepted only if it appears in the offer and looks like a job title. When nothing sure
is found, the position stays empty and the workshop asks the user: no guessing.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from postulo.services.documents.honesty import contains_term, normalize_term
from postulo.services.profile.schema import strip_accents

MAX_TITLE_CHARS = 120
MAX_TITLE_WORDS = 16

_JOB_WORDS = (
    # French
    "stage", "stagiaire", "alternance", "alternant", "alternante", "apprenti", "apprentie",
    "apprentissage", "cdi", "cdd", "fin d'etudes", "pfe", "v.i.e", "these", "doctorat", "doctorant",
    "doctorante", "post-doctorat", "postdoc", "ingenieur", "ingenieure", "developpeur",
    "developpeuse", "analyste", "charge", "chargee", "chef de projet", "cheffe de projet",
    "responsable", "directeur", "directrice", "consultant", "consultante", "technicien",
    "technicienne", "assistant", "assistante", "chercheur", "chercheuse", "comptable", "juriste",
    "commercial", "commerciale", "vendeur", "vendeuse", "infirmier", "infirmiere", "designer",
    "architecte", "administrateur", "administratrice", "auditeur", "auditrice", "controleur",
    "controleuse", "gestionnaire", "coordinateur", "coordinatrice", "animateur", "animatrice",
    "conseiller", "conseillere", "redacteur", "redactrice", "acheteur", "acheteuse", "formateur",
    "formatrice", "manager", "h/f", "f/h", "h/f/x",
    # English
    "intern", "internship", "apprentice", "trainee", "graduate", "engineer", "developer",
    "scientist", "analyst", "officer", "specialist", "associate", "lead", "head of", "director",
    "researcher", "consultant", "architect", "administrator", "coordinator", "owner", "devops",
    "m/f", "m/f/d", "m/w/d",
)  # fmt: skip
_JOB_RE = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(w) for w in _JOB_WORDS) + r")(?![a-z0-9])"
)
_SLOGAN_HINTS_RE = re.compile(
    r"\b(ensemble|avenir|demain|together|future|rejoignez|join us|imaginons|inventons|"
    r"construisons|batissons|agissons|osez)\b|^\w+ons\b|!"
)
_LABEL_RE = re.compile(
    r"^\s*(?P<label>intitule du poste|intitule|poste|titre du poste|titre de l'offre|titre|"
    r"job title|position|fonction|offre)\s*[:\-–]\s*(?P<value>.+)$",
    re.IGNORECASE,
)
_ORG_RE = re.compile(
    r"^\s*(entreprise|societe|organisation|organisme|employeur|structure|etablissement|"
    r"laboratoire|company|employer|organization)\s*[:\-–]\s*(?P<value>.+)$",
    re.IGNORECASE,
)
_CITY_RE = re.compile(
    r"^\s*(lieu de travail|lieu|localisation|ville|location|based in)\s*[:\-–]\s*(?P<value>.+)$",
    re.IGNORECASE,
)
_SENTENCE_START_RE = re.compile(
    r"^(vous|nous|notre|nos|votre|vos|tu|ton|ta|tes|il|elle|ils|elles|on|you|we|our|your|"
    r"the team|l'equipe|au sein|dans le cadre|rattache|rattachee)\b"
)
_AS_RE = re.compile(r"\b(?:en tant que|au poste de|as an?|position of)\s+(?P<value>.+)$", re.I)


class OfferMeta(BaseModel):
    title: str = ""  # empty when nothing sure was found: the user types it
    organization: str = ""
    city: str = ""
    keywords: list[str] = Field(default_factory=list)
    title_found: bool = False
    source: str = "rules"  # "rules" or "ai"


class OfferMetaAI(BaseModel):
    """AI answer of the `offer_meta` prompt (lenient)."""

    model_config = ConfigDict(extra="ignore")
    title: str = ""
    organization: str = ""
    city: str = ""
    keywords: list[str] = Field(default_factory=list)


def _plain(text: str) -> str:
    return strip_accents(text).lower()


def has_job_word(text: str) -> bool:
    return _JOB_RE.search(_plain(text)) is not None


def looks_like_job_title(text: str) -> bool:
    """A short line with a job word. Slogan hints never outweigh a job word."""
    line = text.strip()
    if not line or len(line) > MAX_TITLE_CHARS or len(line.split()) > MAX_TITLE_WORDS:
        return False
    # A sentence addressed to the reader is a description, not a title.
    if _SENTENCE_START_RE.match(_plain(line)):
        return False
    return has_job_word(line)


def is_slogan(text: str) -> bool:
    """A catchphrase: slogan hints and no job word (a job title is never a slogan)."""
    line = text.strip()
    return bool(line) and not has_job_word(line) and bool(_SLOGAN_HINTS_RE.search(_plain(line)))


def _clean_value(value: str) -> str:
    return value.strip().strip(".;!").strip()


def _lines(text: str) -> list[str]:
    return [line.strip(" \t-–•*") for line in text.splitlines() if line.strip(" \t-–•*")]


def extract_offer_meta(offer_text: str) -> OfferMeta:
    """Rule-based extraction, free and offline."""
    meta = OfferMeta()
    lines = _lines(offer_text)
    for line in lines:
        plain = _plain(line)
        if not meta.title and (match := _LABEL_RE.match(plain)):
            start = match.start("value")
            value = _clean_value(line[start:])
            if value and len(value) <= MAX_TITLE_CHARS and not is_slogan(value):
                meta.title, meta.title_found = value, True
        if not meta.organization and (match := _ORG_RE.match(plain)):
            meta.organization = _clean_value(line[match.start("value") :])[:100]
        if not meta.city and (match := _CITY_RE.match(plain)):
            value = _clean_value(line[match.start("value") :])
            meta.city = re.split(r"[(,]", value)[0].strip()[:60]
    if not meta.title:
        for line in lines[:20]:
            if (match := _AS_RE.search(line)) and looks_like_job_title(match.group("value")):
                meta.title, meta.title_found = _clean_value(match.group("value")), True
                break
            if looks_like_job_title(line):
                meta.title, meta.title_found = _clean_value(line), True
                break
    return meta


def valid_ai_title(title: str, offer_text: str) -> bool:
    """The AI position is used only if it is in the offer and looks like a job title."""
    candidate = title.strip()
    return (
        bool(candidate)
        and looks_like_job_title(candidate)
        and normalize_term(candidate) in normalize_term(offer_text)
    )


def merge_ai_meta(rules: OfferMeta, ai: OfferMetaAI, offer_text: str) -> OfferMeta:
    """Combine both: the AI fills or corrects only with values found in the offer."""
    merged = rules.model_copy(deep=True)
    if valid_ai_title(ai.title, offer_text):
        merged.title, merged.title_found, merged.source = ai.title.strip(), True, "ai"
    offer = normalize_term(offer_text)
    if ai.organization.strip() and contains_term(offer, ai.organization):
        merged.organization = ai.organization.strip()
    if ai.city.strip() and contains_term(offer, ai.city):
        merged.city = ai.city.strip()
    merged.keywords = [k.strip() for k in ai.keywords if k.strip()]
    return merged
