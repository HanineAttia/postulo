"""Career library schema (docs/SPEC.md section 6.1).

The profile holds the whole career of the user; each application later selects
the relevant elements. Every list item has a stable internal `id` (used by the UI
for drag and drop and by the merge); the short references (F0, E0...) used in
prompts are computed by `references.py` and never stored.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

# --- normalizers ----------------------------------------------------------------------

_MONTHS = {
    "janvier": 1, "janv": 1, "jan": 1, "january": 1,
    "fevrier": 2, "fevr": 2, "fev": 2, "february": 2, "feb": 2,
    "mars": 3, "march": 3, "mar": 3,
    "avril": 4, "avr": 4, "april": 4, "apr": 4,
    "mai": 5, "may": 5,
    "juin": 6, "june": 6, "jun": 6,
    "juillet": 7, "juil": 7, "july": 7, "jul": 7,
    "aout": 8, "august": 8, "aug": 8,
    "septembre": 9, "sept": 9, "sep": 9, "september": 9,
    "octobre": 10, "oct": 10, "october": 10,
    "novembre": 11, "nov": 11, "november": 11,
    "decembre": 12, "dec": 12, "december": 12,
}  # fmt: skip
_ONGOING = {
    "present", "aujourd'hui", "aujourdhui", "en cours", "actuel", "now", "current", "ce jour"
}  # fmt: skip
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_CHARS_RE = re.compile(r"^\+?[\d\s.\-()/]+$")


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_year_month(value: object) -> str | None:
    """Normalize a date to `AAAA-MM` (or `AAAA`, tolerated). Empty and "present" give None.

    Accepted: 2026-03, 2026, 2026/03, 03/2026, 3/2026, "mars 2026", "Sept. 2025".
    """
    if value is None:
        return None
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str):
        raise ValueError("Date invalide : utilise le format AAAA-MM.")
    text = value.strip()
    if not text or strip_accents(text).lower() in _ONGOING:
        return None
    if m := re.fullmatch(r"(\d{4})(?:[-/.](\d{1,2}))?", text):
        year, month = m.group(1), m.group(2)
        return _ym(year, month)
    if m := re.fullmatch(r"(\d{1,2})[-/.](\d{4})", text):
        return _ym(m.group(2), m.group(1))
    if m := re.fullmatch(r"([A-Za-zÀ-ÿ]+)\.?\s+(\d{4})", text):
        month_num = _MONTHS.get(strip_accents(m.group(1)).lower())
        if month_num:
            return _ym(m.group(2), str(month_num))
    raise ValueError("Date invalide : utilise le format AAAA-MM (par exemple 2026-09).")


def _ym(year: str, month: str | None) -> str:
    if not 1900 <= int(year) <= 2100:
        raise ValueError("Année hors limites.")
    if month is None:
        return year
    if not 1 <= int(month) <= 12:
        raise ValueError("Mois invalide (1 à 12).")
    return f"{year}-{int(month):02d}"


def _empty_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _check_email(value: str | None) -> str | None:
    if value is not None and not _EMAIL_RE.fullmatch(value):
        raise ValueError("Adresse e-mail invalide.")
    return value


def _check_phone(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if not _PHONE_CHARS_RE.fullmatch(value) or not 8 <= len(digits) <= 15:
        raise ValueError("Numéro de téléphone invalide.")
    return value


def _normalize_url(value: str | None) -> str | None:
    if value is None:
        return None
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        if " " in value or "." not in value:
            raise ValueError("Lien invalide.")
        value = "https://" + value
    return value


def _clean_lines(value: object) -> object:
    """Strip list items and drop empty ones (forms send one line per achievement)."""
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return value


YearMonth = Annotated[str | None, BeforeValidator(normalize_year_month)]
Email = Annotated[str | None, BeforeValidator(_empty_to_none), AfterValidator(_check_email)]
Phone = Annotated[str | None, BeforeValidator(_empty_to_none), AfterValidator(_check_phone)]
Url = Annotated[str | None, BeforeValidator(_empty_to_none), AfterValidator(_normalize_url)]
Lines = Annotated[list[str], BeforeValidator(_clean_lines)]


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class _Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class _Item(_Model):
    id: str = Field(default_factory=new_id)


# --- enums (stable codes; the frontend translates them) -------------------------------


class ContractType(StrEnum):
    INTERNSHIP = "internship"
    APPRENTICESHIP = "apprenticeship"
    FIXED_TERM = "fixed_term"
    PERMANENT = "permanent"
    FREELANCE = "freelance"


class Level(StrEnum):
    STUDENT = "student"
    RECENT_GRADUATE = "recent_graduate"
    JUNIOR = "junior"
    EXPERIENCED = "experienced"
    SENIOR = "senior"


class ExperienceType(StrEnum):
    INTERNSHIP = "internship"
    APPRENTICESHIP = "apprenticeship"
    PERMANENT = "permanent"
    FIXED_TERM = "fixed_term"
    FREELANCE = "freelance"
    STUDENT_JOB = "student_job"
    MISSION = "mission"
    RESEARCH = "research"
    VOLUNTEERING = "volunteering"


class ProjectType(StrEnum):
    ACADEMIC = "academic"
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    HACKATHON = "hackathon"
    RESEARCH = "research"
    OPEN_SOURCE = "open_source"


class LanguageLevel(StrEnum):
    NATIVE = "native"
    BILINGUAL = "bilingual"
    C1_C2 = "c1_c2"
    B2 = "b2"
    B1 = "b1"
    A1_A2 = "a1_a2"


# --- sections ---------------------------------------------------------------------------


class Link(_Item):
    label: str = ""
    url: Url = None


class Identity(_Model):
    first_name: str = ""
    last_name: str = ""
    email: Email = None
    phone: Phone = None
    city: str = ""
    mobility: str = ""
    driving_license: bool | None = None
    linkedin: Url = None
    github: Url = None
    portfolio: Url = None
    links: list[Link] = Field(default_factory=list)


class Objective(_Model):
    contract_type: ContractType | None = None
    level: Level | None = None
    domain: str = ""
    target_roles: Lines = Field(default_factory=list)
    availability: YearMonth = None
    duration_months: int | None = Field(default=None, ge=1, le=60)
    remote_ok: bool | None = None
    zones: Lines = Field(default_factory=list)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)


class Education(_Item):
    degree: str = ""
    field: str = ""
    school: str = ""
    city: str = ""
    start: YearMonth = None
    end: YearMonth = None
    honors: str = ""
    key_courses: Lines = Field(default_factory=list)
    details: str = ""


class Experience(_Item):
    title: str = ""
    organization: str = ""
    city: str = ""
    type: ExperienceType | None = None
    start: YearMonth = None
    end: YearMonth = None  # None = ongoing
    context: str = ""
    achievements: Lines = Field(default_factory=list)
    skills: Lines = Field(default_factory=list)


class Project(_Item):
    name: str = ""
    type: ProjectType | None = None
    start: YearMonth = None
    end: YearMonth = None
    context: str = ""
    achievements: Lines = Field(default_factory=list)
    skills: Lines = Field(default_factory=list)
    url: Url = None


class Certification(_Item):
    name: str = ""
    issuer: str = ""
    date: YearMonth = None
    url: Url = None


class Award(_Item):
    title: str = ""
    issuer: str = ""
    date: YearMonth = None
    description: str = ""


class Volunteering(_Item):
    role: str = ""
    organization: str = ""
    start: YearMonth = None
    end: YearMonth = None
    description: str = ""


class Publication(_Item):
    title: str = ""
    venue: str = ""
    date: YearMonth = None
    url: Url = None


class Language(_Item):
    name: str = ""
    level: LanguageLevel | None = None
    certificate: str = ""


class SkillGroup(_Item):
    category: str = ""
    items: Lines = Field(default_factory=list)


class CareerProfile(_Model):
    identity: Identity = Field(default_factory=Identity)
    headline: str = ""
    summary: str = ""
    objective: Objective = Field(default_factory=Objective)
    education: list[Education] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    awards: list[Award] = Field(default_factory=list)
    volunteering: list[Volunteering] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    interests: Lines = Field(default_factory=list)
    extra_facts: Lines = Field(default_factory=list)

    def has_content(self) -> bool:
        """True when the user entered anything (ids and defaults aside)."""
        return _has_content(self.model_dump(exclude={"id"}))


ITEM_SECTIONS: dict[str, type[_Item]] = {
    "education": Education,
    "experiences": Experience,
    "projects": Project,
    "certifications": Certification,
    "awards": Award,
    "volunteering": Volunteering,
    "publications": Publication,
    "languages": Language,
    "skills": SkillGroup,
}


def _has_content(data: Any) -> bool:
    if isinstance(data, dict):
        return any(_has_content(v) for k, v in data.items() if k != "id")
    if isinstance(data, list):
        return len(data) > 0
    return data not in (None, "", False)
