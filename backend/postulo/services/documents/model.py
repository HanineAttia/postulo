"""Render-ready documents (docs/SPEC.md section 7.5).

These models hold exactly what a template prints: every text is final (dates
formatted, sections titled, order decided). They are serialized to `data.json`
for Typst (no escaping needed) and to the Jinja2 context of the HTML engine.
They are also what the user edits in the workshop before a regeneration
without AI, so they stay simple and stable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DocLang = Literal["fr", "en"]
TemplateName = Literal["modern", "classic"]
EngineName = Literal["typst", "html"]

SECTION_KEYS = (
    "education",
    "experiences",
    "projects",
    "skills",
    "certifications",
    "languages",
    "awards",
    "volunteering",
    "publications",
    "interests",
)


class ContactLink(BaseModel):
    label: str  # what is printed ("linkedin.com/in/camille")
    url: str  # what is clicked ("https://www.linkedin.com/in/camille")
    kind: Literal["email", "phone", "linkedin", "github", "portfolio", "other"]


class Contact(BaseModel):
    city: str = ""
    links: list[ContactLink] = Field(default_factory=list)


class Entry(BaseModel):
    ref: str = ""  # F0, E1, P0... (empty for free lines)
    title: str
    subtitle: str = ""  # organization, school, issuer
    location: str = ""
    dates: str = ""
    url: str | None = None  # the title itself becomes the link (SPEC 7.2, lesson 11)
    bullets: list[str] = Field(default_factory=list)
    details: str = ""


class Line(BaseModel):
    label: str = ""  # "Langages", "Anglais" (printed in bold, followed by a colon)
    text: str


class Section(BaseModel):
    key: str  # one of SECTION_KEYS
    title: str
    entries: list[Entry] = Field(default_factory=list)
    lines: list[Line] = Field(default_factory=list)  # skills, languages, interests


class Layout(BaseModel):
    """Visual parameters. Compaction (compact.py) only changes these and the content."""

    template: TemplateName = "modern"
    font: str = "Inter"
    accent: str = "#1D4E89"
    ink: str = "#14213D"
    size: float = 10.0  # pt
    margin_x: float = 14.0  # mm
    margin_y: float = 12.0  # mm
    leading: float = 0.55  # em, space between lines of a paragraph
    gap: float = 3.2  # mm, space before a section title
    item_gap: float = 1.6  # mm, space between entries
    level: int = 0  # compaction level reached (0 to 4)


class CvDocument(BaseModel):
    lang: DocLang = "fr"
    name: str
    title: str
    summary: str = ""
    contact: Contact = Field(default_factory=Contact)
    sections: list[Section] = Field(default_factory=list)
    layout: Layout = Field(default_factory=Layout)

    @property
    def meta_title(self) -> str:
        return f"CV - {self.name}"


class LetterDocument(BaseModel):
    lang: DocLang = "fr"
    name: str
    contact: Contact = Field(default_factory=Contact)
    place_date: str = ""  # "Paris, le 10 novembre 2026"
    recipient: list[str] = Field(default_factory=list)  # organization lines
    subject: str = ""
    salutation: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    layout: Layout = Field(default_factory=Layout)

    @property
    def meta_title(self) -> str:
        prefix = "Lettre de motivation" if self.lang == "fr" else "Cover letter"
        return f"{prefix} - {self.name}"


TEMPLATE_STYLES: dict[TemplateName, dict[str, str]] = {
    "modern": {"font": "Inter", "accent": "#1D4E89", "ink": "#14213D"},
    "classic": {"font": "Source Serif 4", "accent": "#000000", "ink": "#000000"},
}


def layout_for(template: TemplateName) -> Layout:
    return Layout(template=template, **TEMPLATE_STYLES[template])
