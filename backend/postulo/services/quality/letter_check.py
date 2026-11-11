"""Checks of the cover letter (docs/SPEC.md section 16.2).

The letter is free prose written by the AI, so it is checked, not rewritten:
- it names the organization and the exact position;
- it quotes at least two concrete elements of the offer (duties, team, product);
- it never quotes the organization's slogan;
- every sentence is complete: no sentence that ends on "de", "et", "à"..., no pair of
  linking words glued by an assembly of bullet pieces ("un pipeline de et assistant"),
  no truncated "...".
The results are warnings shown in the workshop before sending.
"""

from __future__ import annotations

import re

from postulo.services.documents.honesty import contains_term, normalize_term, tokens
from postulo.services.documents.offer_meta import is_slogan, looks_like_job_title
from postulo.services.quality.layout_check import is_fragment

MIN_OFFER_ELEMENTS = 2
_QUOTED_RE = re.compile(r"«\s*([^»]+?)\s*»|\"([^\"]+)\"|“([^”]+)”")
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
_GLUED_RE = re.compile(
    r"\b(de|du|des|d'|à|au|aux|pour|avec|par|sur|dans|of|for|with|to)\s+(et|ou|de|à|and|or|of)\b",
    re.IGNORECASE,
)
_BULLET_LINE_RE = re.compile(r"^\s*[-–•*▪]\s+(.+)$")


def offer_elements(offer_text: str) -> list[set[str]]:
    """Concrete elements of the offer: its bullet lines (duties, profile), as word sets."""
    elements = [
        tokens(match.group(1))
        for line in offer_text.splitlines()
        if (match := _BULLET_LINE_RE.match(line))
    ]
    if not elements:  # no bullet list: fall back to the sentences of the offer
        elements = [tokens(s) for s in _SENTENCE_RE.findall(offer_text)]
    return [words for words in elements if len(words) >= 3]


def quoted_slogans(paragraphs: list[str], offer_text: str) -> list[str]:
    """Quotes of the letter that are slogans of the offer (never a job title)."""
    text = " ".join(paragraphs)
    offer = normalize_term(offer_text)
    found: list[str] = []
    for groups in _QUOTED_RE.findall(text):
        quote = next(g for g in groups if g).strip()
        if looks_like_job_title(quote):
            continue
        if is_slogan(quote) or (len(quote.split()) >= 3 and normalize_term(quote) in offer):
            found.append(quote)
    for line in offer_text.splitlines():
        if is_slogan(line) and len(line.split()) >= 3 and contains_term(normalize_term(text), line):
            found.append(line.strip())
    return list(dict.fromkeys(found))


def broken_sentences(paragraphs: list[str]) -> list[str]:
    broken: list[str] = []
    for paragraph in paragraphs:
        if "..." in paragraph or "…" in paragraph:
            broken.append(paragraph[:60])
        for sentence in _SENTENCE_RE.findall(paragraph):
            body = sentence.strip().rstrip(".!?").strip()
            if body and (is_fragment(body) or _GLUED_RE.search(body)):
                broken.append(body[-60:])
    return broken


def check_letter(
    paragraphs: list[str], *, offer_text: str, organization: str, position: str
) -> list[str]:
    """French warnings for the user (empty list when the letter passes every check)."""
    warnings: list[str] = []
    text = " ".join(paragraphs)
    if not text.strip():
        return warnings
    normalized = normalize_term(text)
    if organization.strip() and not contains_term(normalized, organization):
        warnings.append(f"La lettre ne nomme pas l'organisation ({organization}).")
    if position.strip() and normalize_term(position) not in normalized:
        warnings.append(f"La lettre ne cite pas l'intitulé exact du poste ({position}).")
    letter_words = tokens(text)
    cited = sum(1 for element in offer_elements(offer_text) if len(element & letter_words) >= 2)
    if cited < MIN_OFFER_ELEMENTS:
        warnings.append(
            "La lettre cite moins de deux éléments concrets de l'offre (missions, équipe, "
            "produit) : elle risque de paraître générique."
        )
    for slogan in quoted_slogans(paragraphs, offer_text):
        warnings.append(f"La lettre reprend le slogan de l'organisation : « {slogan} ».")
    for sentence in broken_sentences(paragraphs):
        warnings.append(f"Phrase incomplète ou mal assemblée dans la lettre : « {sentence} ».")
    return warnings
