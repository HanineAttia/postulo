"""Cleaning of external texts before they reach a prompt (docs/SPEC.md section 5.4).

External texts (offers, CVs, web pages, transcripts) are untrusted data:
- hidden HTML (display:none, visibility:hidden, font-size:0, `hidden`), scripts
  and styles are removed;
- invisible characters (U+200B-U+200F, U+2060-U+206F, U+FEFF, U+00AD) are removed;
- lines that look like instructions aimed at an AI are removed, with a warning;
- the text is truncated to a reasonable length.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

DEFAULT_MAX_CHARS = 40_000

_INVISIBLE_RE = re.compile("[​-‏⁠-⁯﻿­]")
_HIDDEN_STYLE_RE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d]*[1-9])", re.IGNORECASE
)
_INJECTION_RE = re.compile(
    r"|".join(
        [
            r"\bignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+instructions?",
            r"\bdisregard\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above)",
            r"\bforget\s+(all\s+)?(your|previous|prior)\s+instructions?",
            r"\byou\s+are\s+(now\s+)?(an?\s+)?(ai|assistant|language\s+model|chatgpt|claude)\b",
            r"\b(system|developer)\s+prompt\b",
            r"\bnew\s+instructions?\s*:",
            r"\bignore[sz]?\s+(toutes?\s+)?(les\s+)?(instructions?|consignes?)",
            r"\boublie[sz]?\s+(toutes?\s+)?(tes|vos|les)\s+(instructions?|consignes?)",
            r"\btu\s+es\s+(maintenant\s+)?(une?\s+)?(ia|intelligence\s+artificielle|assistant|"
            r"modèle\s+de\s+langage)\b",
            r"\bvous\s+êtes\s+(maintenant\s+)?(une?\s+)?(ia|intelligence\s+artificielle|assistant)\b",
            r"\bnouvelles?\s+(instructions?|consignes?)\s*:",
            r"\b(note|message)\s+(to|for|pour|à|a)\s+(the\s+|l'|l’)?(ai|ia|llm|assistant)\b",
            r"\b(rate|note|évalue|evaluate)\s+(this|ce)\s+(candidate|candidat|cv)\s+.*\b(10/10|100|"
            r"highest|maximum|meilleur)",
        ]
    ),
    re.IGNORECASE,
)
_VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
)
_BLOCK_TAGS = frozenset(
    {"p", "div", "br", "li", "ul", "ol", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section",
     "article", "header", "footer", "table", "blockquote", "pre"}
)  # fmt: skip


@dataclass
class SanitizedText:
    text: str
    warnings: list[str] = field(default_factory=list)
    truncated: bool = False


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._stack: list[bool] = []  # True when the element (or an ancestor) is hidden
        self.hidden_found = False

    @property
    def _hidden(self) -> bool:
        return bool(self._stack) and self._stack[-1]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}
        hidden = (
            tag in ("script", "style", "template", "noscript")
            or "hidden" in attributes
            or attributes.get("aria-hidden") == "true"
            or bool(_HIDDEN_STYLE_RE.search(attributes.get("style", "")))
        )
        if hidden and tag not in ("script", "style"):
            self.hidden_found = True
        if tag in _BLOCK_TAGS and not self._hidden:
            self.parts.append("\n")
        if tag not in _VOID_TAGS:
            self._stack.append(self._hidden or hidden)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS and not self._hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_TAGS or not self._stack:
            return
        self._stack.pop()
        if tag in _BLOCK_TAGS and not self._hidden:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._hidden:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, bool]:
    """Return (visible text, hidden content found)."""
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts), parser.hidden_found


def sanitize_text(
    text: str, *, is_html: bool = False, max_chars: int = DEFAULT_MAX_CHARS
) -> SanitizedText:
    warnings: list[str] = []
    if is_html:
        text, hidden_found = html_to_text(text)
        if hidden_found:
            warnings.append("Du texte caché a été retiré de la page.")
    cleaned = _INVISIBLE_RE.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    kept: list[str] = []
    removed = 0
    for line in cleaned.split("\n"):
        if _INJECTION_RE.search(line):
            removed += 1
            continue
        kept.append(line.rstrip())
    if removed:
        warnings.append(
            f"{removed} ligne(s) qui ressemblaient à des instructions adressées à une IA ont été "
            "retirées du texte."
        )
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    truncated = len(result) > max_chars
    if truncated:
        result = result[:max_chars].rstrip()
        warnings.append("Le texte était très long : seule la première partie a été analysée.")
    return SanitizedText(text=result, warnings=warnings, truncated=truncated)
