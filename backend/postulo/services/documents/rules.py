"""Recognized CV rules (docs/SPEC.md section 16.3, sources in docs/research.md section 5).

Each rule has a stable id. The prompts list them, the simulated jury scores the
application rule by rule and quotes the id in its corrections, and the workshop
shows them. Keep this table in sync with docs/research.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from postulo.services.documents.model import DocLang


@dataclass(frozen=True)
class CvRule:
    id: str
    fr: str
    en: str
    sources: tuple[str, ...]
    langs: tuple[DocLang, ...] = ("fr", "en")  # variants apply to one language only


RULES: tuple[CvRule, ...] = (
    CvRule("R-01", "Verbes d'action, réalisations plutôt que tâches",
           "Action verbs, achievements rather than duties", ("harvard-hes", "harvard-chan")),
    CvRule("R-02", "Résultats chiffrés quand le parcours les contient ; puces au format XYZ "
           "(X accompli, mesuré par Y, en faisant Z)",
           "Quantified results when the career library has them; XYZ bullets "
           "(accomplished X, measured by Y, by doing Z)", ("bock-xyz", "harvard-hes")),
    CvRule("R-03", "Pas de pronoms personnels, pas de « responsable de »",
           "No personal pronouns, no \"responsible for\"", ("harvard-hes", "harvard-chan")),
    CvRule("R-04", "Ordre antéchronologique", "Reverse chronological order",
           ("harvard-hes", "harvard-chan")),
    CvRule("R-05", "Cohérence du gras, de l'italique, des majuscules et de la ponctuation des "
           "puces (aucun point final)",
           "Consistent bold, italics, capitals and bullet punctuation (no final period)",
           ("harvard-chan",)),
    CvRule("R-06", "Équilibre entre texte et espaces blancs ; page remplie entre 85 et 100 %",
           "Balance between text and white space; page filled between 85 and 100 %",
           ("harvard-chan", "spec-16.1")),
    CvRule("R-07", "Même police pour le CV et la lettre", "Same font for the CV and the letter",
           ("harvard-hes",)),
    CvRule("R-08", "Une page pour un étudiant ou un jeune diplômé",
           "One page for a student or a recent graduate", ("harvard-hes", "harvard-chan")),
    CvRule("R-09", "Pas de photo, d'âge ni de situation familiale",
           "No photo, age or marital status", ("harvard-hes",)),
    CvRule("R-10", "Envoi en PDF", "Sent as a PDF", ("harvard-hes",)),
    CvRule("R-11", "Lettre d'une page, adaptée à l'organisation et au poste, qui ne répète pas "
           "le CV", "One-page letter, tailored to the organization and the position, that does "
           "not repeat the CV", ("harvard-hes",)),
    CvRule("R-12", "Variante France : titre explicite, formation d'abord pour un étudiant, "
           "lettre « vous / moi / nous »",
           "France: explicit title, education first for a student, \"you / me / us\" letter",
           ("research-1", "spec-7"), ("fr",)),
    CvRule("R-13", "Variante internationale : section « Summary », mois abrégés en anglais, "
           "format A4 ou Letter", "International: Summary section, English abbreviated "
           "months, A4 or Letter paper", ("harvard-hes",), ("en",)),
    CvRule("R-14", "Mots-clés de l'offre avec leur orthographe exacte quand ils décrivent "
           "fidèlement le parcours", "Offer keywords with their exact spelling when they "
           "truly describe the career", ("research-2",)),
)  # fmt: skip

RULE_IDS = frozenset(rule.id for rule in RULES)


def rules_for(lang: DocLang) -> list[CvRule]:
    return [rule for rule in RULES if lang in rule.langs]


def rules_prompt(lang: DocLang) -> str:
    """One line per rule, for the prompts: `R-01 : ...`."""
    return "\n".join(f"- {rule.id} : {rule.fr}" for rule in rules_for(lang))
