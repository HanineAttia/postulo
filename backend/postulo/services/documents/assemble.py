"""Build render-ready documents from the library and an honest selection (SPEC 7.1, 7.3).

Facts (organizations, dates, schools, cities, links) always come from the
library: the selection only says *which* items and *which wording* of bullets.
Chronological sections are sorted here, newest first, ongoing first (lesson 10).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from urllib.parse import urlparse

from postulo.services.documents import labels, normalize
from postulo.services.documents.model import (
    Contact,
    ContactLink,
    CvDocument,
    DocLang,
    Entry,
    LetterDocument,
    Line,
    Paper,
    Section,
    TemplateName,
    layout_for,
)
from postulo.services.documents.selection import MAX_INTERESTS, SelectedItem, Selection
from postulo.services.profile.references import assign_references
from postulo.services.profile.schema import (
    Award,
    CareerProfile,
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Publication,
    Volunteering,
    strip_accents,
)

_SortKey = Callable[[tuple[str, object]], tuple[int, str, str]]
_FORBIDDEN_TITLES = {"curriculum vitae", "cv", "resume", "curriculum vitae (cv)"}


# --- contact ----------------------------------------------------------------------------------


def _display_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.removeprefix("www.")
    return (host + parsed.path).rstrip("/")


def _tel_url(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    elif digits.startswith("0"):
        digits = "+33" + digits[1:]  # French numbers written nationally
    return "tel:" + digits


def build_contact(profile: CareerProfile) -> Contact:
    ident = profile.identity
    links: list[ContactLink] = []
    if ident.email:
        links.append(ContactLink(label=ident.email, url=f"mailto:{ident.email}", kind="email"))
    if ident.phone:
        links.append(ContactLink(label=ident.phone, url=_tel_url(ident.phone), kind="phone"))
    for kind, url in (
        ("linkedin", ident.linkedin),
        ("github", ident.github),
        ("portfolio", ident.portfolio),
    ):
        if url:
            links.append(ContactLink(label=_display_url(url), url=url, kind=kind))
    for link in ident.links:
        if link.url:
            links.append(
                ContactLink(label=link.label or _display_url(link.url), url=link.url, kind="other")
            )
    return Contact(city=ident.city, links=links)


def full_name(profile: CareerProfile) -> str:
    ident = profile.identity
    return " ".join(part for part in (ident.first_name, ident.last_name) if part).strip()


# --- ordering ---------------------------------------------------------------------------------


def _recency(start: str | None, end: str | None, *, ongoing: bool) -> tuple[int, str, str]:
    """Sort key, newest first: ongoing items, then by end date, then by start date."""
    is_ongoing = 1 if (ongoing and start and not end) else 0
    return (is_ongoing, end or start or "", start or "")


def _refs_sorted[T](
    refs: list[str], table: dict[str, object], kind: type[T], key: _SortKey
) -> list[tuple[str, T]]:
    pairs: list[tuple[str, object]] = [(ref, table[ref]) for ref in refs if ref in table]
    pairs.sort(key=key, reverse=True)
    return [(ref, item) for ref, item in pairs if isinstance(item, kind)]


# --- entries ----------------------------------------------------------------------------------


def _join(*parts: str) -> str:
    return ", ".join(p for p in parts if p)


def _education_entry(ref: str, item: Education, lang: DocLang) -> Entry:
    title = " – ".join(p for p in (item.degree, item.field) if p) or item.school
    details: list[str] = []
    if item.honors:
        details.append(item.honors)
    if item.key_courses:
        details.append(labels.KEY_COURSES[lang] + ", ".join(item.key_courses[:5]))
    if item.details:
        details.append(item.details)
    return Entry(
        ref=ref,
        title=title,
        subtitle=item.school if title != item.school else "",
        location=normalize.city(item.city),
        dates=labels.format_range(item.start, item.end, lang, ongoing=True),
        details=normalize.free_text(". ".join(details), lang),
    )


def _experience_entry(ref: str, item: Experience, chosen: SelectedItem, lang: DocLang) -> Entry:
    return Entry(
        ref=ref,
        title=item.title,
        subtitle=normalize.one_line(item.organization),
        location=normalize.city(item.city),
        dates=labels.format_range(item.start, item.end, lang, ongoing=True),
        bullets=_bullets(chosen.bullets, lang),
    )


def _project_entry(ref: str, item: Project, chosen: SelectedItem, lang: DocLang) -> Entry:
    return Entry(
        ref=ref,
        title=item.name,
        dates=labels.format_range(item.start, item.end, lang, ongoing=False),
        url=item.url,
        bullets=_bullets(chosen.bullets, lang),
    )


def _bullets(bullets: list[str], lang: DocLang) -> list[str]:
    return [text for b in bullets if (text := normalize.bullet(b, lang))]


def _simple_entry(ref: str, item: object, lang: DocLang) -> Entry:
    entry = _raw_simple_entry(ref, item, lang)
    entry.details = normalize.free_text(entry.details, lang)
    return entry


def _raw_simple_entry(ref: str, item: object, lang: DocLang) -> Entry:
    if isinstance(item, Certification):
        return Entry(
            ref=ref,
            title=item.name,
            subtitle=item.issuer,
            dates=labels.format_month(item.date, lang),
            url=item.url,
        )
    if isinstance(item, Award):
        return Entry(
            ref=ref,
            title=item.title,
            subtitle=item.issuer,
            dates=labels.format_month(item.date, lang),
            details=item.description,
        )
    if isinstance(item, Volunteering):
        return Entry(
            ref=ref,
            title=item.role,
            subtitle=item.organization,
            dates=labels.format_range(item.start, item.end, lang, ongoing=True),
            details=item.description,
        )
    if isinstance(item, Publication):
        return Entry(
            ref=ref,
            title=item.title,
            subtitle=item.venue,
            dates=labels.format_month(item.date, lang),
            url=item.url,
        )
    raise TypeError(f"Unexpected item {type(item).__name__}")  # pragma: no cover


def _language_line(item: Language, lang: DocLang) -> Line:
    level = labels.LANGUAGE_LEVELS[lang].get(item.level.value) if item.level else None
    detail = ", ".join(p for p in (level, item.certificate) if p)
    return Line(label=item.name, text=detail) if detail else Line(text=item.name)


def clean_title(title: str, profile: CareerProfile) -> str:
    """Never 'Curriculum vitae' (SPEC 7.1): fall back to the headline or a target role."""
    text = title.strip()
    if strip_accents(text).lower() in _FORBIDDEN_TITLES or not text:
        text = profile.headline or (profile.objective.target_roles or [""])[0]
    return text


# --- CV -----------------------------------------------------------------------------------------


def build_cv(
    profile: CareerProfile,
    selection: Selection,
    *,
    lang: DocLang = "fr",
    template: TemplateName = "modern",
    paper: Paper = "a4",
) -> CvDocument:
    table: dict[str, object] = dict(assign_references(profile))
    titles = labels.SECTION_TITLES[lang]
    sections: dict[str, Section] = {}

    def by_dates(pair: tuple[str, object]) -> tuple[int, str, str]:
        item = pair[1]
        start = getattr(item, "start", None) or getattr(item, "date", None)
        end = getattr(item, "end", None) if hasattr(item, "end") else start
        return _recency(start, end, ongoing=hasattr(item, "end"))

    education = _refs_sorted(selection.education, table, Education, by_dates)
    if education:
        sections["education"] = Section(
            key="education",
            title=titles["education"],
            entries=[_education_entry(ref, item, lang) for ref, item in education],
        )

    chosen_exp = {c.ref: c for c in selection.experiences}
    experiences = _refs_sorted(list(chosen_exp), table, Experience, by_dates)
    if experiences:
        sections["experiences"] = Section(
            key="experiences",
            title=titles["experiences"],
            entries=[_experience_entry(r, i, chosen_exp[r], lang) for r, i in experiences],
        )

    projects = [
        _project_entry(c.ref, item, c, lang)
        for c in selection.projects
        if isinstance(item := table.get(c.ref), Project)
    ]  # relevance order, as chosen
    if projects:
        sections["projects"] = Section(key="projects", title=titles["projects"], entries=projects)

    skill_lines = [
        Line(label=g.category, text=", ".join(g.items)) for g in selection.skills if g.items
    ]
    if skill_lines:
        sections["skills"] = Section(key="skills", title=titles["skills"], lines=skill_lines)

    for key, kind in (
        ("certifications", Certification),
        ("awards", Award),
        ("volunteering", Volunteering),
        ("publications", Publication),
    ):
        refs: list[str] = getattr(selection, key)
        pairs = _refs_sorted(refs, table, kind, by_dates)
        if pairs:
            sections[key] = Section(
                key=key,
                title=titles[key],
                entries=[_simple_entry(ref, item, lang) for ref, item in pairs],
            )

    language_lines = [
        _language_line(item, lang)
        for ref in selection.languages
        if isinstance(item := table.get(ref), Language) and item.name
    ]
    if language_lines:
        sections["languages"] = Section(
            key="languages", title=titles["languages"], lines=language_lines
        )

    interests = [i for i in selection.interests if i][:MAX_INTERESTS]
    if interests:
        sections["interests"] = Section(
            key="interests", title=titles["interests"], lines=[Line(text=", ".join(interests))]
        )

    ordered = [sections[key] for key in selection.section_order if key in sections]
    ordered += [s for key, s in sections.items() if key not in selection.section_order]
    return CvDocument(
        lang=lang,
        name=full_name(profile),
        title=normalize.one_line(clean_title(selection.title, profile)),
        summary=normalize.free_text(selection.summary, lang),
        contact=build_contact(profile),
        sections=ordered,
        layout=layout_for(template, paper),
    )


# --- letter -------------------------------------------------------------------------------------

_SALUTATION: dict[DocLang, str] = {"fr": "Madame, Monsieur,", "en": "Dear Hiring Manager,"}
_CLOSING: dict[DocLang, str] = {
    "fr": "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.",
    "en": "Yours sincerely,",
}


_RECRUITMENT: dict[DocLang, str] = {"fr": "Service recrutement", "en": "Recruitment team"}
_SUBJECT: dict[DocLang, str] = {"fr": "Objet : Candidature – ", "en": "Subject: Application – "}


def letter_subject(position: str, lang: DocLang) -> str:
    """'Objet : Candidature – <exact position>' (SPEC 16.1), built here, never by the AI."""
    return _SUBJECT[lang] + normalize.one_line(position) if position.strip() else ""


def build_letter(
    profile: CareerProfile,
    paragraphs: list[str],
    *,
    organization: str = "",
    position: str = "",
    offer_city: str = "",
    lang: DocLang = "fr",
    template: TemplateName = "modern",
    paper: Paper = "a4",
    today: date | None = None,
) -> LetterDocument:
    day = today or date.today()
    long_date = labels.long_date(day.year, day.month, day.day, lang)
    city = normalize.city(profile.identity.city)
    if lang == "fr":
        place_date = f"{city}, le {long_date}" if city else f"Le {long_date}"
    else:
        place_date = f"{city}, {long_date}" if city else long_date
    texts = [text for p in paragraphs if (text := normalize.paragraph(p, lang))]
    subject = letter_subject(position, lang)
    if lang == "fr":
        texts = [french_typography(p) for p in texts]
        subject = french_typography(subject)
    recipient = (
        [normalize.one_line(organization), _RECRUITMENT[lang], normalize.city(offer_city)]
        if organization.strip()
        else []
    )
    return LetterDocument(
        lang=lang,
        name=full_name(profile),
        contact=build_contact(profile),
        place_date=place_date,
        recipient=[line for line in recipient if line],
        subject=subject,
        salutation=_SALUTATION[lang],
        paragraphs=texts,
        closing=_CLOSING[lang],
        layout=layout_for(template, paper),
    )


# --- typography and placeholders ----------------------------------------------------------------

NBSP = chr(0xA0)  # no-break space
NNBSP = chr(0x202F)  # narrow no-break space, before ; ! ? in French
_QUOTES_RE = re.compile(r"[\"“]\s*([^\"“”]+?)\s*[\"”]")
_HIGH_PUNCT_RE = re.compile(r"(?<=\S)[ \u00a0\u202f]*([;!?])(?=\s|$|[»\"”)])")
_COLON_RE = re.compile(r"(?<=[^\s:/\d])[ \u00a0\u202f]*:(?=\s|$)")
_GUILLEMETS_RE = re.compile(r"«[ \u00a0\u202f]*(.*?)[ \u00a0\u202f]*»")


def french_typography(text: str) -> str:
    """French spacing (SPEC 7.3): no-break spaces before : ; ! ? and inside « »."""
    text = _QUOTES_RE.sub(lambda m: f"«{m.group(1)}»", text)
    text = _GUILLEMETS_RE.sub(lambda m: f"«{NBSP}{m.group(1)}{NBSP}»", text)
    text = _HIGH_PUNCT_RE.sub(lambda m: f"{NNBSP}{m.group(1)}", text)
    return _COLON_RE.sub(f"{NBSP}:", text)


_BRACKET_RE = re.compile(r"\[([^\[\]]{1,60})\]")


def fill_placeholders(text: str, profile: CareerProfile, *, organization: str = "",
                      role: str = "") -> str:  # fmt: skip
    """Replace '[Prénom Nom]'-like placeholders from the profile; drop unknown ones (lesson 12)."""
    ident = profile.identity
    values: list[tuple[tuple[str, ...], str]] = [
        (("telephone", "phone", "tel", "portable", "mobile"), ident.phone or ""),
        (("mail", "courriel"), ident.email or ""),
        (("linkedin",), ident.linkedin or ""),
        (("github",), ident.github or ""),
        (("entreprise", "organisation", "organization", "company", "societe"), organization),
        (("poste", "position", "role", "intitule", "job"), role),
        (("prenom", "first"), ident.first_name),
        (("nom", "name", "signature"), full_name(profile)),
        (("ville", "city"), ident.city),
    ]

    def replace(match: re.Match[str]) -> str:
        key = strip_accents(match.group(1)).lower()
        if "prenom" in key and "nom" in key.replace("prenom", ""):
            return full_name(profile)
        for needles, value in values:
            if any(n in key for n in needles):
                return value
        return ""

    filled = _BRACKET_RE.sub(replace, text)
    filled = re.sub(r"[ \t]{2,}", " ", filled)
    return re.sub(r" +([,.])", r"\1", filled).strip()


# --- file names ---------------------------------------------------------------------------------


def _slug(text: str) -> str:
    ascii_text = strip_accents(text)
    words = re.findall(r"[A-Za-z0-9]+", ascii_text)
    return "-".join(words)[:60]


def document_filename(kind: str, profile: CareerProfile, organization: str) -> str:
    """CV_Prenom-Nom_Organisation.pdf (SPEC 7.5). Organization is optional."""
    parts = [kind, _slug(full_name(profile)) or "Candidat", _slug(organization)]
    return "_".join(p for p in parts if p) + ".pdf"


# --- e-mail signature ---------------------------------------------------------------------------

_EMAIL_CLOSING: dict[DocLang, str] = {"fr": "Bien cordialement,", "en": "Kind regards,"}
_CLOSING_WORDS = ("cordialement", "salutations", "bien a vous", "regards", "sincerely", "best")
_PHONE_LIKE_RE = re.compile(r"(?:\+?\d[\s.\-]?){8,}")


def email_signature(profile: CareerProfile) -> list[str]:
    """First and last name, phone and LinkedIn, only those present in the profile."""
    ident = profile.identity
    lines = [full_name(profile), ident.phone or "", ident.linkedin or ""]
    return [line for line in lines if line]


def with_signature(body: str, profile: CareerProfile, lang: DocLang) -> str:
    """Replace whatever signature the AI wrote by the one built from the profile (correction a).

    Trailing lines that look like a signature (name, phone, e-mail, links, placeholders) are
    removed; a closing formula is added if missing; then the profile signature is appended.
    """
    name = strip_accents(full_name(profile)).lower()
    lines = body.rstrip().split("\n")

    def is_signature(line: str) -> bool:
        text = strip_accents(line.strip()).lower()
        return (
            not text
            or (bool(name) and text == name)
            or text.startswith("[")
            or "@" in text
            or "linkedin" in text
            or "http" in text
            or text.startswith(("tel", "phone", "mobile", "portable"))
            or _PHONE_LIKE_RE.fullmatch(text) is not None
        )

    while lines and is_signature(lines[-1]):
        lines.pop()
    last = strip_accents(lines[-1]).lower() if lines else ""
    if not any(word in last for word in _CLOSING_WORDS):
        lines += ["", _EMAIL_CLOSING[lang]]
    return "\n".join([*lines, *email_signature(profile)])
