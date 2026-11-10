"""Deterministic workshop answers for the MockProvider (tests and demo mode).

No AI: the answers are built from the library and the offer found in the prompt.
They stay honest (original bullets, library skills) so the demo shows the real
pipeline: the jury gives 74/100 first, then 8.4 (a score on 10, normalized to
84 by jury.py) after the revision, to show the before/after display.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from postulo.services.profile.schema import strip_accents

_STOP = frozenset(
    re.findall(
        r"\S+",
        "avec dans pour nous vous votre notre leurs cette sont être avoir mission missions poste "
        "profil équipe equipe entreprise stage stagiaire travail offre description about with "
        "your will team that this from have ",
    )
)


def _block(prompt: str, tag: str) -> str:
    start = prompt.rfind(f"<{tag}>")
    end = prompt.rfind(f"</{tag}>")
    return prompt[start + len(tag) + 2 : end].strip() if 0 <= start < end else ""


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", strip_accents(text).lower()).split())


def _has(haystack: str, term: str) -> bool:
    needle = _norm(term)
    return (
        bool(needle)
        and re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None
    )


def _fence(payload: Any) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=1) + "\n```"


def _organization(offer: str) -> str:
    for line in offer.splitlines():
        match = re.match(
            r"\s*(entreprise|soci[ée]t[ée]|organisation|employeur|company)\s*:\s*(.+)", line, re.I
        )
        if match:
            return match.group(2).strip()[:80]
    return ""


def _title(offer: str, library: dict[str, Any]) -> str:
    for line in offer.splitlines():
        match = re.match(r"\s*(intitul[ée]|poste|titre|job title)\s*:\s*(.+)", line, re.I)
        if match:
            return match.group(2).strip()[:90]
    first = next((line.strip() for line in offer.splitlines() if line.strip()), "")
    return first[:90] if first and len(first) <= 90 else str(library.get("headline", ""))


def _keywords(offer: str, library: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(library skills named in the offer, offer words absent from the library)."""
    offer_norm = _norm(offer)
    skills: list[str] = []
    for group in library.get("skills", []):
        skills.extend(group.get("items", []))
    for item in library.get("items", {}).values():
        skills.extend(item.get("skills", []))
    found: list[str] = []
    for skill in skills:
        if _has(offer_norm, skill) and skill not in found:
            found.append(skill)
    # The organization's own name is not a keyword.
    library_norm = _norm(json.dumps(library, ensure_ascii=False) + " " + _organization(offer))
    words = Counter(
        w for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ+#-]{4,}", offer) if w.lower() not in _STOP
    )
    missing = [
        w for w, _ in sorted(words.items(), key=lambda kv: (-kv[1], kv[0]))
        if not _has(library_norm, w)
    ][:2]  # fmt: skip
    return found[:18], missing


def mock_application_draft(prompt: str) -> str:
    try:
        library: dict[str, Any] = json.loads(_block(prompt, "library") or "{}")
    except json.JSONDecodeError:
        library = {}
    offer = _block(prompt, "offer")
    items: dict[str, dict[str, Any]] = library.get("items", {})
    refs = {prefix: [r for r in items if r.startswith(prefix)] for prefix in "FEPCRAUL"}
    found, missing = _keywords(offer, library)
    offer_norm = _norm(offer)
    groups = sorted(
        library.get("skills", []),
        key=lambda g: -sum(_has(offer_norm, i) for i in g.get("items", [])),
    )
    title = _title(offer, library)
    organization = _organization(offer)

    achievements = [a for r in refs["E"] + refs["P"] for a in items[r].get("achievements", [])]
    proofs = " ".join(achievements[:3]) or "Mes expériences m'ont appris à livrer des résultats."
    where = organization or "votre organisation"
    letter = [
        f"Votre offre « {title} » a retenu toute mon attention. Elle décrit un poste où la "
        "qualité des données, la rigueur des analyses et la mise en production comptent autant "
        "que les modèles eux-mêmes. C'est exactement ce que je recherche pour la prochaine étape "
        f"de mon parcours, et c'est pourquoi je souhaite rejoindre {where}. Les missions "
        "présentées, comme l'environnement technique décrit, correspondent aux compétences que "
        "j'ai déjà mises en pratique en entreprise et en projet.",
        f"Au cours de mes expériences, j'ai obtenu des résultats concrets. {proofs} Ces "
        "réalisations m'ont appris à travailler avec des équipes métier, à documenter mon "
        "travail et à présenter des résultats clairs à des personnes qui ne sont pas "
        "spécialistes. Elles m'ont aussi appris à mesurer l'effet réel d'un modèle avant de le "
        "déployer.",
        "Je peux mettre cette expérience au service de vos projets dès la date de démarrage "
        "prévue, avec la même exigence de qualité et de transparence. Je souhaite "
        "vous présenter mes travaux plus en détail et d'échanger sur vos priorités lors d'un "
        "entretien, à la date qui vous conviendra. Je reste disponible pour tout complément "
        "d'information sur mon parcours et sur les projets cités.",
    ]
    draft = {
        "offer": {"title": title, "organization": organization, "keywords": found + missing},
        "cv": {
            "title": title,
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
        "letter": {"subject": f"Candidature : {title}", "paragraphs": letter},
        "email": {
            "subject": f"Candidature : {title}",
            "body": (
                "Madame, Monsieur,\n\n"
                f"Je vous adresse ma candidature pour le poste « {title} ». Vous trouverez en "
                "pièces jointes mon CV et ma lettre de motivation, qui détaillent mes "
                "expériences et les résultats obtenus sur des projets proches de vos besoins. "
                "Je souhaite échanger avec vous lors d'un entretien, à la date qui "
                "vous conviendra.\n\nJe vous remercie pour votre attention et reste "
                "disponible pour tout complément d'information.\n\n"
                "Bien cordialement,\n[Prénom Nom]\n[Téléphone]"
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
    tips.append("La révision a mis en avant les éléments les plus proches de l'offre.")
    draft["tips"] = tips
    return _fence(draft)


def mock_jury(prompt: str) -> str:
    second_round = re.search(r"^ROUND:\s*2\b", prompt, re.MULTILINE) is not None
    if second_round:
        criteria = {"fit": 9, "impact": 8, "clarity": 9, "keywords": 8, "credibility": 9,
                    "letter": 8, "form": 8}  # fmt: skip
        payload: dict[str, Any] = {
            "score": 8.4,  # on 10: jury.py normalizes it to 84
            "decision": "interview",
            "six_second_impression": "Profil clair et ciblé, réalisations chiffrées visibles.",
            "criteria": criteria,
            "strengths": ["Réalisations chiffrées", "Mots-clés de l'offre présents"],
            "corrections": [
                {"priority": "low", "target": "letter", "text": "Raccourcir la conclusion."}
            ],
        }
    else:
        criteria = {"fit": 8, "impact": 7, "clarity": 8, "keywords": 7, "credibility": 8,
                    "letter": 7, "form": 7}  # fmt: skip
        payload = {
            "score": 74,
            "decision": "maybe",
            "six_second_impression": "Bon profil technique, le lien avec l'offre pourrait être "
            "plus direct.",
            "criteria": criteria,
            "strengths": ["Parcours technique solide", "CV lisible sur une page"],
            "corrections": [
                {"priority": "high", "target": "cv",
                 "text": "Mettre en premier les réalisations les plus proches de l'offre."},
                {"priority": "medium", "target": "letter",
                 "text": "Citer un élément concret de l'organisation dans le premier paragraphe."},
                {"priority": "low", "target": "email", "text": "Préciser la date de début."},
            ],
        }  # fmt: skip
    return _fence(payload)
