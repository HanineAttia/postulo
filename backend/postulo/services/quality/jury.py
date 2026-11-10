"""Simulated jury (docs/SPEC.md section 7.6).

Three roles (recruiter, hiring manager, ATS specialist) read the CV text *as the
ATS extracted it*, the letter and the offer. The answer is validated leniently,
then normalized: a score given on 10 instead of 100 (lesson 6) is multiplied by
10 when the criteria confirm it, criteria are clamped to 0-10 and decisions are
mapped to stable codes.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from postulo.services import prompts
from postulo.services.documents.model import DocLang
from postulo.services.llm.base import LLMProvider
from postulo.services.llm.json_utils import complete_json
from postulo.services.prompts.sanitize import sanitize_text

CRITERIA = ("fit", "impact", "clarity", "keywords", "credibility", "letter", "form")
Decision = Literal["interview", "maybe", "reject"]
Priority = Literal["high", "medium", "low"]

_DECISIONS: dict[str, Decision] = {
    "interview": "interview", "entretien": "interview", "yes": "interview", "oui": "interview",
    "maybe": "maybe", "peut-etre": "maybe", "peut-être": "maybe", "peut etre": "maybe",
    "reject": "reject", "refus": "reject", "rejet": "reject", "no": "reject", "non": "reject",
}  # fmt: skip
_PRIORITIES: dict[str, Priority] = {
    "high": "high", "haute": "high", "medium": "medium", "moyenne": "medium",
    "low": "low", "basse": "low",
}  # fmt: skip


class _RawCorrection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    priority: str = "medium"
    target: str = ""
    text: str = ""


class RawJury(BaseModel):
    model_config = ConfigDict(extra="ignore")
    score: float
    decision: str = ""
    six_second_impression: str = ""
    criteria: dict[str, Any] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    corrections: list[_RawCorrection] = Field(default_factory=list)


class Correction(BaseModel):
    priority: Priority
    target: str
    text: str


class JuryReport(BaseModel):
    score: int  # on 100
    decision: Decision
    six_second_impression: str
    criteria: dict[str, float]  # each on 10
    strengths: list[str]
    corrections: list[Correction]


def _criterion(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number > 10:  # given on 100
        number /= 10
    return max(0.0, min(10.0, number))


def normalize_score(raw: float, criteria: dict[str, float]) -> int:
    """Score on 100. A score <= 10 is read as a score on 10 when the criteria agree."""
    score = raw
    if 0 < raw <= 10:
        mean = sum(criteria.values()) / len(criteria) if criteria else None
        if mean is None or abs(mean - raw) <= 2.5:
            score = raw * 10
    return round(max(0.0, min(100.0, score)))


def normalize_jury(raw: RawJury) -> JuryReport:
    criteria = {
        key: value for key in CRITERIA if (value := _criterion(raw.criteria.get(key))) is not None
    }
    score = normalize_score(raw.score, criteria)
    decision = _DECISIONS.get(raw.decision.strip().lower())
    if decision is None:
        decision = "interview" if score >= 80 else "maybe" if score >= 60 else "reject"
    order = {"high": 0, "medium": 1, "low": 2}
    corrections = sorted(
        (
            Correction(
                priority=_PRIORITIES.get(c.priority.strip().lower(), "medium"),
                target=c.target.strip().lower() or "cv",
                text=c.text.strip(),
            )
            for c in raw.corrections
            if c.text.strip()
        ),
        key=lambda c: order[c.priority],
    )
    return JuryReport(
        score=score,
        decision=decision,
        six_second_impression=raw.six_second_impression.strip(),
        criteria=criteria,
        strengths=[s.strip() for s in raw.strengths if s.strip()],
        corrections=corrections,
    )


def build_jury_prompt(
    cv_text: str, letter_text: str, offer_text: str, lang: DocLang, round_number: int
) -> str:
    return prompts.render(
        "jury",
        round=round_number,
        lang_name="en français" if lang == "fr" else "for an English-speaking recruiter",
        cv_text=sanitize_text(cv_text).text,
        letter_text=sanitize_text(letter_text).text,
        offer_text=offer_text,
    )


async def run_jury(
    provider: LLMProvider,
    *,
    cv_text: str,
    letter_text: str,
    offer_text: str,
    lang: DocLang,
    round_number: int,
    timeout: int = 300,
) -> JuryReport:
    prompt = build_jury_prompt(cv_text, letter_text, offer_text, lang, round_number)
    raw = await complete_json(provider, prompt, RawJury, timeout=timeout)
    return normalize_jury(raw)
