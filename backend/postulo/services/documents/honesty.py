"""Honesty guard (docs/SPEC.md section 7.4).

Turns an AI draft into a `Selection` that only contains what the library holds:
1. only references are taken from the AI; facts are rebuilt later from the library;
2. unknown references are ignored, with a warning;
3. skills absent from the library are removed and reported;
4. interests absent from the library are removed;
5. an empty experience or project selection, while the library has some, is
   replaced by a fallback selection based on keyword similarity with the offer;
6. the draft is never modified in place (deep copy; lesson 5).

Extra checks, same spirit: a rewritten bullet (or the summary) that contains a
number absent from its source is replaced by the original wording, and offer
keywords that do not appear in the offer are dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from postulo.services.documents.draft import ApplicationDraft, DraftItem, prompt_library
from postulo.services.documents.selection import (
    MAX_INTERESTS,
    Limits,
    SelectedItem,
    Selection,
    SkillCategory,
    complete_order,
    limits_for,
)
from postulo.services.profile.references import assign_references
from postulo.services.profile.schema import CareerProfile, Experience, Project, strip_accents

MAX_KEYWORDS = 25
_PARENS_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_DIGIT_GROUP_RE = re.compile(r"(?<=\d)[   .](?=\d{3}\b)")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.-]*")
_STOPWORDS = frozenset(
    re.findall(
        r"\S+",
        "les des une un la le et en du de dans pour par sur avec aux au est sont vous nous notre "
        "votre vos nos ses son sa leur leurs qui que quoi dont ou mais plus tres the and for with "
        "you your our are will this that from have has into etc ainsi cette ces afin entre chez ",
    )
)


def normalize_term(text: str) -> str:
    """Comparison key: no accents, no case, no parentheses, single spaces (SPEC 7.4)."""
    text = _PARENS_RE.sub(" ", strip_accents(text).lower())
    text = re.sub(r"[^a-z0-9+#]+", " ", text)
    return " ".join(text.split())


def contains_term(haystack_normalized: str, term: str) -> bool:
    """Whole-word match of `term` in an already normalized text."""
    needle = normalize_term(term)
    if not needle:
        return False
    return (
        re.search(rf"(?<![a-z0-9+#]){re.escape(needle)}(?![a-z0-9+#])", haystack_normalized)
        is not None
    )


def numbers_in(text: str) -> set[str]:
    """Numbers of a text, '12 000' and '12000' alike, '3,5' and '3.5' alike."""
    joined = _DIGIT_GROUP_RE.sub("", text)
    return {n.replace(",", ".") for n in _NUMBER_RE.findall(joined)}


def tokens(text: str) -> set[str]:
    return {t for t in _WORD_RE.findall(normalize_term(text)) if len(t) > 2} - _STOPWORDS


def offer_tokens(offer_text: str) -> set[str]:
    """Meaningful words of an offer, to measure the relevance of a library element."""
    return tokens(offer_text)


@dataclass
class GuardResult:
    selection: Selection
    keywords: list[str]
    warnings: list[str] = field(default_factory=list)
    removed_skills: list[str] = field(default_factory=list)


def _item_text(item: Experience | Project) -> str:
    title = item.title if isinstance(item, Experience) else item.name
    parts = [title, item.context, *item.achievements, *item.skills]
    if isinstance(item, Experience):
        parts.append(item.organization)
    return " ".join(parts)


def _entries(profile: CareerProfile) -> list[Experience | Project]:
    return [*profile.experiences, *profile.projects]


def _library_skills(profile: CareerProfile) -> dict[str, str]:
    """Normalized skill -> library spelling, from skills, experiences and projects."""
    skills: dict[str, str] = {}
    for group in profile.skills:
        for item in group.items:
            skills.setdefault(normalize_term(item), item)
    for entry in _entries(profile):
        for item in entry.skills:
            skills.setdefault(normalize_term(item), item)
    skills.pop("", None)
    return skills


def _not_skills(profile: CareerProfile) -> set[str]:
    """Languages and certifications never go in the skills section (SPEC 7.1)."""
    names = {normalize_term(lang.name) for lang in profile.languages}
    names |= {normalize_term(cert.name) for cert in profile.certifications}
    return names - {""}


class _Guard:
    def __init__(self, profile: CareerProfile, offer_text: str) -> None:
        self.profile = profile
        self.offer_text = offer_text
        self.refs = assign_references(profile)
        self.limits: Limits = limits_for(profile)
        self.warnings: list[str] = []
        self.allowed_numbers = numbers_in(" ".join(profile.extra_facts))

    # --- references -----------------------------------------------------------------------

    def _known(self, ref: str, prefix: str, seen: set[str]) -> bool:
        if ref in seen:
            return False
        seen.add(ref)
        if not ref.startswith(prefix) or ref not in self.refs:
            self.warnings.append(f"Référence inconnue ignorée : {ref}.")
            return False
        return True

    def plain_refs(self, refs: list[str], prefix: str) -> list[str]:
        seen: set[str] = set()
        return [ref for ref in refs if self._known(ref, prefix, seen)]

    def items(
        self, chosen: list[DraftItem], prefix: str, limit: int, per_item: int
    ) -> list[SelectedItem]:
        seen: set[str] = set()
        result: list[SelectedItem] = []
        for item in chosen:
            if not self._known(item.ref, prefix, seen) or len(result) >= limit:
                continue
            source = self.refs[item.ref]
            assert isinstance(source, Experience | Project)
            result.append(SelectedItem(ref=item.ref, bullets=self.bullets(item, source, per_item)))
        return result

    # --- bullets ----------------------------------------------------------------------------

    def bullets(self, item: DraftItem, source: Experience | Project, limit: int) -> list[str]:
        """Rewritten bullets, checked: a number absent from the source brings the original back."""
        originals = list(source.achievements)
        allowed = numbers_in(_item_text(source)) | self.allowed_numbers
        unused = list(originals)
        result: list[str] = []
        for bullet in (b.strip() for b in item.bullets):
            if not bullet:
                continue
            invented = numbers_in(bullet) - allowed
            if invented:
                replacement = self._closest(bullet, unused)
                self.warnings.append(
                    f"Chiffre absent de ton parcours retiré ({', '.join(sorted(invented))}) : "
                    "la puce d'origine a été reprise."
                )
                if replacement is None:
                    continue
                bullet = replacement
            if bullet in unused:
                unused.remove(bullet)
            result.append(bullet)
        if not result:
            result = originals
        return result[:limit]

    @staticmethod
    def _closest(bullet: str, candidates: list[str]) -> str | None:
        if not candidates:
            return None
        words = tokens(bullet)
        best = max(candidates, key=lambda c: len(words & tokens(c)))
        candidates.remove(best)
        return best

    # --- skills and interests ---------------------------------------------------------------

    def skills(self, groups: list[SkillCategory]) -> tuple[list[SkillCategory], list[str]]:
        library = _library_skills(self.profile)
        excluded = _not_skills(self.profile)
        removed: list[str] = []
        kept_groups: list[SkillCategory] = []
        seen: set[str] = set()
        for group in groups:
            items: list[str] = []
            for raw in group.items:
                key = normalize_term(raw)
                if not key or key in seen:
                    continue
                if key in library and key not in excluded:
                    seen.add(key)
                    items.append(library[key])
                elif key not in excluded:
                    removed.append(raw.strip())
            if items:
                kept_groups.append(SkillCategory(category=group.category.strip(), items=items))
        if removed:
            self.warnings.append(
                "Compétences retirées car absentes de ton parcours : "
                f"{', '.join(removed)}. Si tu les maîtrises, ajoute-les puis régénère."
            )
        if not kept_groups:
            kept_groups = [
                SkillCategory(category=g.category, items=list(g.items))
                for g in self.profile.skills
                if g.items
            ]
        return kept_groups[: self.limits.skill_categories], removed

    def interests(self, proposed: list[str]) -> list[str]:
        library = {normalize_term(i): i for i in self.profile.interests}
        kept: list[str] = []
        dropped: list[str] = []
        for raw in proposed:
            key = normalize_term(raw)
            if key in library and library[key] not in kept:
                kept.append(library[key])
            elif key:
                dropped.append(raw.strip())
        if dropped:
            self.warnings.append(
                f"Centres d'intérêt retirés car absents de ton parcours : {', '.join(dropped)}."
            )
        return kept[:MAX_INTERESTS]

    def summary(self, proposed: str) -> str:
        text = proposed.strip()
        if not text:
            return self.profile.summary
        profile = self.profile
        objective = profile.objective
        sources = [profile.summary, profile.headline, *profile.extra_facts, self.offer_text]
        sources += [_item_text(i) for i in _entries(profile)]
        sources.append(f"{objective.availability or ''} {objective.duration_months or ''}")
        # Small counts ("2 expériences", "3 projets") are always fine.
        allowed = numbers_in(" ".join(sources)) | {str(n) for n in range(1, 11)}
        if numbers_in(text) - allowed:
            self.warnings.append(
                "L'accroche contenait un chiffre absent de ton parcours : ton accroche "
                "habituelle a été reprise."
            )
            return self.profile.summary
        return text

    # --- fallback ---------------------------------------------------------------------------

    def fallback(
        self, items: list[Experience] | list[Project], prefix: str, limit: int, per_item: int
    ) -> list[SelectedItem]:
        offer = tokens(self.offer_text)
        scored = sorted(
            range(len(items)), key=lambda i: (-len(offer & tokens(_item_text(items[i]))), i)
        )
        return [
            SelectedItem(ref=f"{prefix}{i}", bullets=items[i].achievements[:per_item])
            for i in scored[:limit]
        ]

    def keywords(self, proposed: list[str]) -> list[str]:
        offer = normalize_term(self.offer_text)
        result: list[str] = []
        seen: set[str] = set()
        for raw in proposed:
            key = normalize_term(raw)
            if key and key not in seen and contains_term(offer, raw):
                seen.add(key)
                result.append(raw.strip())
        return result[:MAX_KEYWORDS]


def apply_guard(draft: ApplicationDraft, profile: CareerProfile, offer_text: str) -> GuardResult:
    """Build an honest selection from `draft`. `draft` itself is never modified."""
    cv = draft.cv.model_copy(deep=True)
    guard = _Guard(profile, offer_text)
    limits = guard.limits

    experiences = guard.items(
        cv.experiences, "E", limits.experiences, limits.bullets_per_experience
    )
    if not experiences and profile.experiences:
        experiences = guard.fallback(
            profile.experiences, "E", limits.experiences, limits.bullets_per_experience
        )
        guard.warnings.append(
            "L'IA n'a sélectionné aucune expérience : une sélection automatique a été faite "
            "selon les mots-clés de l'offre."
        )
    projects = guard.items(cv.projects, "P", limits.projects, limits.bullets_per_project)
    if not projects and profile.projects:
        projects = guard.fallback(
            profile.projects, "P", limits.projects, limits.bullets_per_project
        )
        guard.warnings.append(
            "L'IA n'a sélectionné aucun projet : une sélection automatique a été faite selon "
            "les mots-clés de l'offre."
        )
    education = guard.plain_refs(cv.education, "F") or [
        f"F{i}" for i in range(len(profile.education))
    ]
    languages = guard.plain_refs(cv.languages, "L") or [
        f"L{i}" for i in range(len(profile.languages))
    ]
    skills, removed = guard.skills(
        [SkillCategory(category=g.category, items=g.items) for g in cv.skills]
    )
    selection = Selection(
        title=cv.title.strip(),
        summary=guard.summary(cv.summary),
        section_order=complete_order(cv.section_order, profile),
        education=education,
        experiences=experiences,
        projects=projects,
        certifications=guard.plain_refs(cv.certifications, "C"),
        awards=guard.plain_refs(cv.awards, "R"),
        volunteering=guard.plain_refs(cv.volunteering, "A"),
        publications=guard.plain_refs(cv.publications, "U"),
        languages=languages,
        skills=skills,
        interests=guard.interests(cv.interests),
    )
    return GuardResult(
        selection=selection,
        keywords=guard.keywords(draft.offer.keywords),
        warnings=guard.warnings,
        removed_skills=removed,
    )


def letter_warnings(paragraphs: list[str], profile: CareerProfile, offer_text: str) -> list[str]:
    """The letter is free prose: numbers absent from the library and the offer are flagged."""
    allowed = numbers_in(json.dumps(prompt_library(profile), ensure_ascii=False))
    allowed |= numbers_in(offer_text)
    allowed |= {str(n) for n in range(1, 11)}
    text = " ".join(paragraphs)
    warnings: list[str] = []
    if invented := numbers_in(text) - allowed:
        warnings.append(
            "La lettre cite des chiffres absents de ton parcours et de l'offre "
            f"({', '.join(sorted(invented))}) : vérifie-les avant d'envoyer."
        )
    words = len(text.split())
    if paragraphs and not 250 <= words <= 330:
        warnings.append(f"La lettre fait {words} mots (objectif : 250 à 330).")
    return warnings
