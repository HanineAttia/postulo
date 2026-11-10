"""Merge an imported profile into the library without duplicates, and describe the changes.

Matching uses normalized keys (accents, case and punctuation ignored), so the
same experience written "Data Scientist - ACME" and "data scientist, Acme" is
recognized. For a matched item, empty fields are filled and lists are united;
fields the user already filled are never overwritten ("kept").
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel

from postulo.services.profile.schema import ITEM_SECTIONS, CareerProfile, new_id, strip_accents

# Fields that identify an item, per section. All empty => the item never matches.
_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "education": ("school", "degree"),
    "experiences": ("organization", "title"),
    "projects": ("name",),
    "certifications": ("name",),
    "awards": ("title",),
    "volunteering": ("organization", "role"),
    "publications": ("title",),
    "languages": ("name",),
    "skills": ("category",),
}
_LABEL_FIELDS: dict[str, tuple[str, ...]] = {
    "education": ("degree", "field", "school"),
    "experiences": ("title", "organization"),
    "projects": ("name",),
    "certifications": ("name", "issuer"),
    "awards": ("title", "issuer"),
    "volunteering": ("role", "organization"),
    "publications": ("title", "venue"),
    "languages": ("name",),
    "skills": ("category",),
}
_LINE_SECTIONS = ("interests", "extra_facts")


def normalize(text: object) -> str:
    if not isinstance(text, str):
        return ""
    lowered = strip_accents(text).lower()
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", lowered).split())


class SectionDiff(BaseModel):
    section: str
    added: list[str]
    updated: list[str]
    unchanged: int
    current_count: int
    incoming_count: int


class FieldDiff(BaseModel):
    path: str
    current: str | None
    incoming: str | None
    action: Literal["filled", "kept", "extended"]


class ImportDiff(BaseModel):
    sections: list[SectionDiff]
    fields: list[FieldDiff]

    @property
    def has_changes(self) -> bool:
        return bool(self.fields) or any(s.added or s.updated for s in self.sections)


def merge_profiles(
    current: CareerProfile, incoming: CareerProfile
) -> tuple[CareerProfile, ImportDiff]:
    """Return (merged profile, description of what the merge adds or keeps)."""
    cur = current.model_dump(mode="json")
    inc = incoming.model_dump(mode="json")
    fields: list[FieldDiff] = []

    _merge_object(cur["identity"], inc["identity"], "identity", fields)
    _merge_object(cur["objective"], inc["objective"], "objective", fields)
    for scalar in ("headline", "summary"):
        _merge_value(cur, inc, scalar, scalar, fields)

    sections = [_merge_section(cur, inc, name) for name in ITEM_SECTIONS]
    for name in _LINE_SECTIONS:
        before = list(cur[name])
        cur[name] = union_lines(before, inc[name])
        added = cur[name][len(before) :]
        sections.append(
            SectionDiff(
                section=name,
                added=added,
                updated=[],
                unchanged=len(inc[name]) - len(added),
                current_count=len(before),
                incoming_count=len(inc[name]),
            )
        )
    return CareerProfile.model_validate(cur), ImportDiff(sections=sections, fields=fields)


def describe_replace(current: CareerProfile, incoming: CareerProfile) -> ImportDiff:
    """Diff for the "replace" mode: everything incoming is new, nothing is kept."""
    cur = current.model_dump(mode="json")
    inc = incoming.model_dump(mode="json")
    sections = [
        SectionDiff(
            section=name,
            added=[_label(name, item) for item in inc[name]],
            updated=[],
            unchanged=0,
            current_count=len(cur[name]),
            incoming_count=len(inc[name]),
        )
        for name in ITEM_SECTIONS
    ]
    sections += [
        SectionDiff(
            section=name,
            added=list(inc[name]),
            updated=[],
            unchanged=0,
            current_count=len(cur[name]),
            incoming_count=len(inc[name]),
        )
        for name in _LINE_SECTIONS
    ]
    return ImportDiff(sections=sections, fields=[])


def union_lines(current: list[str], incoming: list[str]) -> list[str]:
    """Keep `current` order, append new lines from `incoming` (normalized comparison)."""
    seen = {normalize(line) for line in current}
    result = list(current)
    for line in incoming:
        key = normalize(line)
        if key and key not in seen:
            seen.add(key)
            result.append(line)
    return result


# --- internals ---------------------------------------------------------------------------


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _merge_value(
    cur: dict[str, Any], inc: dict[str, Any], key: str, path: str, fields: list[FieldDiff] | None
) -> None:
    current_value, incoming_value = cur.get(key), inc.get(key)
    if _is_empty(incoming_value):
        return
    if isinstance(incoming_value, list) and all(isinstance(v, str) for v in incoming_value):
        current_list = current_value if isinstance(current_value, list) else []
        merged = union_lines(current_list, incoming_value)
        if len(merged) > len(current_list):
            cur[key] = merged
            if fields is not None:
                fields.append(
                    FieldDiff(
                        path=path,
                        current=", ".join(current_list) or None,
                        incoming=", ".join(merged[len(current_list) :]),
                        action="extended" if current_list else "filled",
                    )
                )
        return
    if _is_empty(current_value):
        cur[key] = incoming_value
        if fields is not None:
            fields.append(
                FieldDiff(path=path, current=None, incoming=str(incoming_value), action="filled")
            )
    elif normalize(str(current_value)) != normalize(str(incoming_value)) and fields is not None:
        fields.append(
            FieldDiff(
                path=path, current=str(current_value), incoming=str(incoming_value), action="kept"
            )
        )


def _merge_object(
    cur: dict[str, Any], inc: dict[str, Any], prefix: str, fields: list[FieldDiff]
) -> None:
    for key, value in inc.items():
        if key == "links":
            cur["links"] = _merge_links(cur.get("links", []), value, fields)
        else:
            _merge_value(cur, inc, key, f"{prefix}.{key}", fields)


def _merge_links(
    current: list[dict[str, Any]], incoming: list[dict[str, Any]], fields: list[FieldDiff]
) -> list[dict[str, Any]]:
    known = {normalize(link.get("url")) for link in current}
    result = list(current)
    for link in incoming:
        key = normalize(link.get("url"))
        if key and key not in known:
            known.add(key)
            result.append({**link, "id": new_id()})
            fields.append(
                FieldDiff(
                    path="identity.links", current=None, incoming=link.get("url"), action="filled"
                )
            )
    return result


def _key(section: str, item: dict[str, Any]) -> tuple[str, ...] | None:
    key = tuple(normalize(item.get(name)) for name in _KEY_FIELDS[section])
    return key if any(key) else None


def _same_item(section: str, a: dict[str, Any], b: dict[str, Any]) -> bool:
    key_a, key_b = _key(section, a), _key(section, b)
    if key_a is None or key_a != key_b:
        return False
    # Same organization and title but different start dates: two distinct periods.
    start_a, start_b = a.get("start"), b.get("start")
    return not (start_a and start_b and start_a[:4] != start_b[:4])


def _label(section: str, item: dict[str, Any]) -> str:
    parts = [str(item[name]) for name in _LABEL_FIELDS[section] if item.get(name)]
    return " · ".join(parts) or "(sans titre)"


def _merge_section(cur: dict[str, Any], inc: dict[str, Any], section: str) -> SectionDiff:
    current_items: list[dict[str, Any]] = cur[section]
    current_count = len(current_items)
    added: list[str] = []
    updated: list[str] = []
    unchanged = 0
    used_ids = {item["id"] for item in current_items}
    for item in inc[section]:
        index = next(
            (i for i, existing in enumerate(current_items) if _same_item(section, existing, item)),
            None,
        )
        if index is None:
            new_item = dict(item)
            if new_item.get("id") in used_ids:
                new_item["id"] = new_id()
            used_ids.add(new_item["id"])
            current_items.append(new_item)
            added.append(_label(section, item))
            continue
        existing = current_items[index]
        before = dict(existing)
        for key in item:
            if key != "id":
                _merge_value(existing, item, key, key, None)
        if existing != before:
            updated.append(_label(section, existing))
        else:
            unchanged += 1
    return SectionDiff(
        section=section,
        added=added,
        updated=updated,
        unchanged=unchanged,
        current_count=current_count,
        incoming_count=len(inc[section]),
    )
