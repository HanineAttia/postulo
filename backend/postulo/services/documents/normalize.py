"""Normalization of free texts before rendering (docs/SPEC.md section 16.1).

Applied to what is printed (CV, letter, e-mail), never to the library itself:
- no line break inside a summary, a context or a bullet (CV imports often cut lines);
- single spaces; no leading bullet sign;
- "~95 %" becomes "environ 95 %" ("about" in English), "500K" becomes "500 000",
  "1,2M" becomes "1,2 million";
- bullets never end with a period (rule R-05: one convention for every bullet);
- cities get an initial capital ("cergy" -> "Cergy").
"""

from __future__ import annotations

import re

from postulo.services.documents.model import DocLang

NBSP = " "
_SPACES_RE = re.compile(r"[ \t  ]+")
_LINEBREAKS_RE = re.compile(r"\s*[\r\n]+\s*")
_BULLET_SIGN_RE = re.compile(r"^\s*(?:[-–—•·*▪◦●]|\d+[.)])\s+")
_TILDE_RE = re.compile(r"(?<![\w~])~\s*(?=\d)")
_NUMBER = r"(\d+(?:[.,]\d+)?)"
_THOUSANDS_RE = re.compile(_NUMBER + r"\s?[kK](?![A-Za-zÀ-ÿ])")
_MILLIONS_RE = re.compile(_NUMBER + r"\s?M(?![A-Za-zÀ-ÿ])")
_ABOUT: dict[DocLang, str] = {"fr": "environ ", "en": "about "}


def _group_thousands(value: int, lang: DocLang) -> str:
    text = f"{value:,}"
    return text.replace(",", NBSP) if lang == "fr" else text


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def _expand_numbers(text: str, lang: DocLang) -> str:
    text = _TILDE_RE.sub(_ABOUT[lang], text)

    def thousands(match: re.Match[str]) -> str:
        return _group_thousands(round(_to_float(match.group(1)) * 1000), lang)

    def millions(match: re.Match[str]) -> str:
        raw = match.group(1)
        number = raw.replace(".", ",") if lang == "fr" else raw.replace(",", ".")
        if lang == "fr":
            return f"{number} million" + ("s" if _to_float(raw) >= 2 else "")
        return f"{number} million"

    text = _THOUSANDS_RE.sub(thousands, text)
    return _MILLIONS_RE.sub(millions, text)


def one_line(text: str) -> str:
    """Join the lines of a text and squeeze the spaces."""
    return _SPACES_RE.sub(" ", _LINEBREAKS_RE.sub(" ", text)).strip()


def free_text(text: str, lang: DocLang) -> str:
    """Summary, context, details: one line, readable numbers."""
    return _expand_numbers(one_line(text), lang)


def bullet(text: str, lang: DocLang) -> str:
    """A CV bullet: one line, no leading sign, no final period."""
    cleaned = free_text(_BULLET_SIGN_RE.sub("", text.strip()), lang)
    if cleaned.endswith(".") and not cleaned.endswith(("..", "etc.")):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def paragraph(text: str, lang: DocLang) -> str:
    """A letter paragraph: one line, readable numbers, final punctuation kept."""
    return free_text(text, lang)


def email_body(text: str, lang: DocLang) -> str:
    """E-mail: line breaks kept (paragraphs), numbers made readable, spaces squeezed."""
    lines = [_SPACES_RE.sub(" ", line).strip() for line in text.replace("\r\n", "\n").split("\n")]
    joined = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return _expand_numbers(joined, lang)


def city(text: str) -> str:
    """Initial capitals for a city typed in lower or upper case ("SAINT-DENIS" -> "Saint-Denis")."""
    value = one_line(text)
    if not value or (not value.islower() and not value.isupper()):
        return value
    small = {"de", "du", "des", "la", "le", "les", "sur", "en", "et"}
    words = re.split(r"([ -])", value.lower())
    out = []
    for index, word in enumerate(words):
        if word in (" ", "-") or (index > 0 and word in small):
            out.append(word)
        else:
            out.append(word[:1].upper() + word[1:])
    return "".join(out)
