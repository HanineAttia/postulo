"""Deterministic workshop answers for the MockProvider (tests and demo mode).

No AI: the answers are built from the library, the position and the offer found in
the prompt. They follow the same rules as a real answer (SPEC 7, 16.2, 16.3):
- the letter names the organization and the exact position, quotes two duties of the
  offer, never the slogan, and is made of complete sentences (bullets are never glued
  together: one whole bullet is quoted after a colon);
- offer keywords are short (1 to 3 words) and never a language;
- tips and gaps speak to the user with "tu"; the e-mail is not signed (the server adds
  the signature from the profile).
The jury gives 74/100 first, then 8.4 (a score on 10, normalized to 84 by jury.py) after
the revision, to show the before/after display, with a verdict per rule (R-xx).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from postulo.services.documents.honesty import is_short_keyword
from postulo.services.documents.offer_meta import extract_offer_meta, is_slogan
from postulo.services.documents.rules import RULES
from postulo.services.profile.schema import strip_accents
from postulo.services.quality.layout_check import is_fragment

_STOP = frozenset(
    re.findall(
        r"\S+",
        "avec dans pour nous vous votre notre leurs cette sont etre avoir mission missions poste "
        "profil equipe entreprise stage stagiaire travail offre description about with your will "
        "team that this from have",
    )
)
_LANGUAGES = frozenset({"anglais", "francais", "espagnol", "allemand", "english", "french"})
_BULLET_RE = re.compile(r"^\s*[-–•*]\s+(.+?)\s*\.?\s*$")
_TARGET_WORDS = 265


def _block(prompt: str, tag: str) -> str:
    start = prompt.rfind(f"<{tag}>")
    end = prompt.rfind(f"</{tag}>")
    return prompt[start + len(tag) + 2 : end].strip() if 0 <= start < end else ""


def _line_value(prompt: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}\s*:\s*(.+)$", prompt, re.MULTILINE)
    value = match.group(1).strip() if match else ""
    return "" if value in ("non précisée", "non precisee") else value


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", strip_accents(text).lower()).split())


def _has(haystack: str, term: str) -> bool:
    needle = _norm(term)
    pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
    return bool(needle) and re.search(pattern, haystack) is not None


def _fence(payload: Any) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=1) + "\n```"


def _keywords(offer: str, library: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(library skills named in the offer, short offer words absent from the library)."""
    offer_norm = _norm(offer)
    skills: list[str] = []
    for group in library.get("skills", []):
        skills.extend(group.get("items", []))
    for item in library.get("items", {}).values():
        skills.extend(item.get("skills", []))
    found: list[str] = []
    for skill in skills:
        if _has(offer_norm, skill) and skill not in found and is_short_keyword(skill):
            found.append(skill)
    library_norm = _norm(json.dumps(library, ensure_ascii=False))
    organization = extract_offer_meta(offer).organization
    words = Counter(
        w
        for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ+#-]{4,}", offer)
        if _norm(w) not in _STOP and _norm(w) not in _LANGUAGES and not _has(_norm(organization), w)
    )
    missing = [
        w for w, _ in sorted(words.items(), key=lambda kv: (-kv[1], kv[0]))
        if not _has(library_norm, w)
    ][:2]  # fmt: skip
    return found[:18], missing


def _duties(offer: str) -> list[str]:
    """Bullet lines of the offer, as lower-case clauses without final period."""
    duties = []
    for line in offer.splitlines():
        match = _BULLET_RE.match(line)
        if match and not is_slogan(match.group(1)):
            text = match.group(1).rstrip(" .;")
            duties.append(text[:1].lower() + text[1:])
    return duties


def _proof(items: dict[str, dict[str, Any]], refs: list[str]) -> str:
    """One whole, complete bullet with a number, introduced by a full sentence."""
    for ref in refs:
        item = items[ref]
        for bullet in item.get("achievements", []):
            text = bullet.strip().rstrip(".")
            if re.search(r"\d", text) and not is_fragment(text):
                where = item.get("organization") or item.get("name") or ""
                role = item.get("title") or item.get("name") or ""
                lead = (
                    f"Chez {where}, en tant que {role.lower()}"
                    if item.get("organization")
                    else (f"Dans le projet « {role} »")
                )
                return f"{lead}, un résultat résume bien ma démarche : « {text} »."
    return "Mes expériences m'ont appris à mesurer l'effet réel de mon travail."


def _letter(position: str, organization: str, offer: str, items: dict[str, Any],
            refs: list[str]) -> list[str]:  # fmt: skip
    where = organization or "votre équipe"
    duties = _duties(offer)
    first = duties[0] if duties else "les missions décrites dans votre offre"
    second = duties[1] if len(duties) > 1 else "le travail avec les équipes métier"
    paragraphs = [
        f"Votre offre « {position} » chez {where} a retenu toute mon attention. "
        f"Deux missions me motivent particulièrement : {first}, et {second}. Elles correspondent "
        "aux compétences que j'ai déjà mises en pratique en entreprise et en projet, et au "
        "métier que je souhaite exercer.",
        f"{_proof(items, refs)} Ces expériences m'ont appris à travailler avec des équipes "
        "métier, à documenter mon travail et à présenter des résultats clairs à des personnes "
        "qui ne sont pas spécialistes. Elles m'ont aussi appris à vérifier l'effet réel d'un "
        "modèle avant de le déployer, et à organiser mon travail en équipe sur des projets "
        "exigeants, avec des délais courts et des priorités qui évoluent.",
        f"Rejoindre {where} me permettrait de mettre cette rigueur au service de vos projets "
        "dès la date de démarrage prévue, avec la même exigence de qualité et de transparence. "
        "Je souhaite vous présenter mes travaux plus en détail et échanger sur vos priorités "
        "lors d'un entretien, à la date qui vous conviendra.",
    ]
    fillers = (
        "Je reste disponible pour tout complément d'information sur mon parcours et sur les "
        "projets cités dans mon CV.",
        "Je peux aussi vous transmettre des exemples de mes travaux avant notre échange.",
        "Je vous remercie par avance pour l'attention que vous porterez à ma candidature.",
    )
    for sentence in fillers:
        if len(" ".join(paragraphs).split()) >= _TARGET_WORDS:
            break
        paragraphs[2] += " " + sentence
    return paragraphs


def mock_application_draft(prompt: str) -> str:
    try:
        library: dict[str, Any] = json.loads(_block(prompt, "library") or "{}")
    except json.JSONDecodeError:
        library = {}
    offer = _block(prompt, "offer")
    position = _line_value(prompt, "Intitulé exact du poste") or extract_offer_meta(offer).title
    organization = _line_value(prompt, "Organisation") or extract_offer_meta(offer).organization
    items: dict[str, dict[str, Any]] = library.get("items", {})
    refs = {prefix: [r for r in items if r.startswith(prefix)] for prefix in "FEPCRAUL"}
    found, missing = _keywords(offer, library)
    offer_norm = _norm(offer)
    groups = sorted(
        library.get("skills", []),
        key=lambda g: -sum(_has(offer_norm, i) for i in g.get("items", [])),
    )
    # Tools named in the offer and used in an experience or project, but missing from the
    # skill groups, join the most relevant group (they come from the library: still honest).
    grouped = {_norm(i) for g in groups for i in g.get("items", [])}
    extra = [s for s in found if _norm(s) not in grouped]
    if groups and extra:
        groups[0] = {**groups[0], "items": [*groups[0].get("items", []), *extra]}

    draft = {
        "offer": {"title": position, "organization": organization, "keywords": found + missing},
        "cv": {
            "title": position,
            "summary": library.get("summary", ""),
            "section_order": [],
            "education": refs["F"],
            "experiences": [
                {"ref": r, "bullets": items[r].get("achievements", [])} for r in refs["E"][:3]
            ],
            "projects": [
                {"ref": r, "bullets": items[r].get("achievements", [])} for r in refs["P"][:3]
            ],
            "certifications": refs["C"],
            "awards": refs["R"],
            "volunteering": refs["A"],
            "publications": refs["U"],
            "languages": refs["L"],
            "skills": groups,
            "interests": library.get("interests", [])[:3],
        },
        "letter": {"paragraphs": _letter(position, organization, offer, items, refs["E"])},
        "email": {
            "body": (
                "Madame, Monsieur,\n\n"
                f"Je vous adresse ma candidature pour le poste de {position}. Vous trouverez en "
                "pièces jointes mon CV et ma lettre de motivation, qui détaillent mes "
                "expériences et les résultats obtenus sur des projets proches de vos besoins. "
                "Je souhaite échanger avec vous lors d'un entretien, à la date qui vous "
                "conviendra.\n\nJe vous remercie pour votre attention et reste disponible pour "
                "tout complément d'information.\n\nBien cordialement,"
            ),
        },
        "tips": [
            "Cherche sur LinkedIn la personne qui encadrera le poste et cite un de ses projets "
            "dans ton message.",
            "Prépare un exemple chiffré de ton expérience la plus proche de l'offre pour "
            "l'entretien.",
        ],
        "gaps": [f"L'offre mentionne « {w} », absent de ton parcours." for w in missing],
    }
    return _fence(draft)


def mock_application_revision(prompt: str) -> str:
    try:
        draft: dict[str, Any] = json.loads(_block(prompt, "draft") or "{}")
    except json.JSONDecodeError:
        return mock_application_draft(prompt)
    tips = list(draft.get("tips", []))
    tips.append(
        "Relis la version corrigée : elle met en avant les éléments les plus proches de l'offre."
    )
    draft["tips"] = tips
    return _fence(draft)


def mock_offer_meta(prompt: str) -> str:
    meta = extract_offer_meta(_block(prompt, "offer"))
    return _fence(
        {"title": meta.title, "organization": meta.organization, "city": meta.city, "keywords": []}
    )


def mock_jury(prompt: str) -> str:
    second_round = re.search(r"^ROUND:\s*2\b", prompt, re.MULTILINE) is not None
    rules = [{"id": rule.id, "ok": True, "comment": ""} for rule in RULES]
    if second_round:
        criteria = {"fit": 9, "impact": 8, "clarity": 9, "keywords": 8, "credibility": 9,
                    "letter": 8, "form": 8}  # fmt: skip
        payload: dict[str, Any] = {
            "score": 8.4,  # on 10: jury.py normalizes it to 84
            "decision": "interview",
            "six_second_impression": "Profil clair et ciblé, réalisations chiffrées visibles.",
            "criteria": criteria,
            "strengths": ["Réalisations chiffrées", "Mots-clés de l'offre présents"],
            "rules": rules,
            "corrections": [
                {"priority": "low", "target": "letter", "rule": "R-11",
                 "text": "Raccourcir la conclusion."}
            ],
        }  # fmt: skip
    else:
        criteria = {"fit": 8, "impact": 7, "clarity": 8, "keywords": 7, "credibility": 8,
                    "letter": 7, "form": 7}  # fmt: skip
        rules[1] = {"id": "R-02", "ok": False, "comment": "Une puce sans résultat mesurable."}
        payload = {
            "score": 74,
            "decision": "maybe",
            "six_second_impression": "Bon profil technique, le lien avec l'offre pourrait être "
            "plus direct.",
            "criteria": criteria,
            "strengths": ["Parcours technique solide", "CV lisible sur une page"],
            "rules": rules,
            "corrections": [
                {"priority": "high", "target": "cv", "rule": "R-02",
                 "text": "Mettre en premier les réalisations chiffrées proches de l'offre."},
                {"priority": "medium", "target": "letter", "rule": "R-11",
                 "text": "Citer un élément concret de l'organisation dans le premier paragraphe."},
                {"priority": "low", "target": "email", "rule": "",
                 "text": "Préciser la date de début."},
            ],
        }  # fmt: skip
    return _fence(payload)
