"""Career library: schema, references, lenient import, completeness, merge, backup, store."""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from postulo.services.profile import store
from postulo.services.profile.backup import BackupError, export_profile, parse_backup
from postulo.services.profile.completeness import CHECKS, compute_completeness
from postulo.services.profile.lenient import validate_lenient
from postulo.services.profile.merge import merge_profiles, normalize, union_lines
from postulo.services.profile.references import assign_references
from postulo.services.profile.sample import sample_profile
from postulo.services.profile.schema import (
    CareerProfile,
    Experience,
    Identity,
    Objective,
    normalize_year_month,
)

# --- schema ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-03", "2026-03"),
        ("2026", "2026"),
        (2026, "2026"),
        ("2026/3", "2026-03"),
        ("03/2026", "2026-03"),
        ("mars 2026", "2026-03"),
        ("Sept. 2025", "2025-09"),
        ("Février 2024", "2024-02"),
        ("", None),
        ("Présent", None),
        ("en cours", None),
        (None, None),
    ],
)
def test_year_month_normalization(raw: object, expected: str | None) -> None:
    assert normalize_year_month(raw) == expected


@pytest.mark.parametrize("raw", ["2026-13", "demain", "26-03", "1850"])
def test_year_month_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError, match=r"Date|Mois|Année"):
        normalize_year_month(raw)


def test_identity_validation() -> None:
    identity = Identity(email="  a.b@example.com ", phone="+33 6 12 34 56 78", linkedin="")
    assert identity.email == "a.b@example.com"
    assert identity.linkedin is None
    assert Identity(github="github.com/me").github == "https://github.com/me"
    with pytest.raises(ValidationError, match="e-mail"):
        Identity(email="not-an-email")
    with pytest.raises(ValidationError, match="téléphone"):
        Identity(phone="12")
    with pytest.raises(ValidationError, match="téléphone"):
        Identity(phone="06 12 34 abc")


def test_lines_are_cleaned_and_ids_assigned() -> None:
    experience = Experience(title="Stage", achievements=["  Fait A ", "", "   ", "Fait B"])
    assert experience.achievements == ["Fait A", "Fait B"]
    assert len(experience.id) == 12
    assert Experience().id != Experience().id


def test_objective_bounds() -> None:
    with pytest.raises(ValidationError):
        Objective(duration_months=0)
    with pytest.raises(ValidationError):
        Objective.model_validate({"contract_type": "stage"})


def test_has_content() -> None:
    assert not CareerProfile().has_content()
    assert CareerProfile(headline="Data").has_content()
    assert CareerProfile(experiences=[Experience()]).has_content()


def test_sample_profile_is_valid_and_fictional() -> None:
    profile = sample_profile()
    assert profile.identity.first_name == "Camille"
    assert profile.identity.last_name == "Exemple"
    assert profile.identity.email is not None
    assert profile.identity.email.endswith("@example.com")
    assert compute_completeness(profile).score >= 90


# --- references --------------------------------------------------------------------------


def test_references_follow_display_order() -> None:
    profile = sample_profile()
    refs = assign_references(profile)
    assert refs["E0"] is profile.experiences[0]
    assert refs["E1"] is profile.experiences[1]
    assert refs["F0"] is profile.education[0]
    assert refs["P1"] is profile.projects[1]
    assert refs["L2"] is profile.languages[2]
    assert refs["R0"] is profile.awards[0]
    assert refs["A0"] is profile.volunteering[0]
    assert "U0" not in refs  # no publication
    profile.experiences.reverse()
    first = assign_references(profile)["E0"]
    assert isinstance(first, Experience)
    assert first.title == "Assistante de recherche"


# --- lenient validation -------------------------------------------------------------------


def test_lenient_drops_invalid_fields_and_warns() -> None:
    raw: dict[str, Any] = {
        "identity": {"first_name": "Léa", "email": "pas-un-email"},
        "experiences": [
            {"title": "Stage", "start": "bientôt", "type": "stage d'été"},
            {"title": "CDD", "start": "2024-01"},
        ],
        "objective": {"contract_type": "internship"},
    }
    profile, warnings = validate_lenient(raw)
    assert profile.identity.first_name == "Léa"
    assert profile.identity.email is None
    assert profile.experiences[0].title == "Stage"
    assert profile.experiences[0].start is None
    assert profile.experiences[0].type is None
    assert profile.experiences[1].start == "2024-01"
    assert len(warnings) == 3
    assert raw["identity"]["email"] == "pas-un-email"  # input left untouched


def test_lenient_rejects_non_objects() -> None:
    profile, warnings = validate_lenient(["a"])
    assert not profile.has_content()
    assert warnings


# --- completeness ------------------------------------------------------------------------


def test_completeness_points_sum_to_100() -> None:
    assert sum(check.points for check in CHECKS) == 100


def test_completeness_empty_profile() -> None:
    result = compute_completeness(CareerProfile())
    assert result.score == 0
    keys = [a.key for a in result.advice]
    assert keys[0] == "quantified"  # the biggest loss first
    assert {"target_roles", "projects", "linkedin"} <= set(keys)


def test_completeness_quantified_achievements() -> None:
    profile = sample_profile()
    for experience in profile.experiences:
        experience.achievements = ["Travaillé sur des données", "Aidé l'équipe"]
    for project in profile.projects:
        project.achievements = ["Construit un prototype"]
    result = compute_completeness(profile)
    advice = next(a for a in result.advice if a.key == "quantified")
    assert advice.params == {"count": 0, "total": 6}
    assert advice.points == 10


def test_completeness_partial_projects() -> None:
    profile = sample_profile()
    profile.projects = profile.projects[:1]
    advice = next(a for a in compute_completeness(profile).advice if a.key == "projects")
    assert advice.points == 4
    assert advice.params == {"count": 1}


# --- merge -------------------------------------------------------------------------------


def test_normalize_and_union_lines() -> None:
    assert normalize("  Data Scientist - ACMÉ ") == "data scientist acme"
    assert normalize("C++ / C#") == "c++ c#"
    assert union_lines(["Python", "SQL"], ["python", "Docker", "sql ", "Docker"]) == [
        "Python",
        "SQL",
        "Docker",
    ]


def test_merge_same_profile_is_idempotent() -> None:
    profile = sample_profile()
    merged, diff = merge_profiles(profile, sample_profile())
    assert merged == profile
    assert not diff.has_changes
    experiences = next(s for s in diff.sections if s.section == "experiences")
    assert experiences.unchanged == 2


def test_merge_fills_empty_fields_and_keeps_existing() -> None:
    current = CareerProfile(
        identity=Identity(first_name="Camille", email="camille@example.com"),
        experiences=[
            Experience(
                title="Data scientist",
                organization="ACME",
                start="2026-04",
                achievements=["Modèle de fraude"],
            )
        ],
    )
    incoming = CareerProfile(
        identity=Identity(first_name="Camille", email="autre@example.com", city="Paris"),
        headline="Data scientist",
        experiences=[
            Experience(
                title="data scientist",
                organization="Acmé",
                start="2026-05",
                city="Paris",
                achievements=["modèle de fraude", "Pipeline 3x plus rapide"],
            ),
            Experience(title="Stage", organization="Beta"),
        ],
    )
    merged, diff = merge_profiles(current, incoming)
    assert merged.identity.email == "camille@example.com"
    assert merged.identity.city == "Paris"
    assert merged.headline == "Data scientist"
    assert len(merged.experiences) == 2
    first = merged.experiences[0]
    assert first.id == current.experiences[0].id
    assert first.start == "2026-04"
    assert first.city == "Paris"
    assert first.achievements == ["Modèle de fraude", "Pipeline 3x plus rapide"]
    actions = {f.path: f.action for f in diff.fields}
    assert actions["identity.email"] == "kept"
    assert actions["identity.city"] == "filled"
    experiences = next(s for s in diff.sections if s.section == "experiences")
    assert experiences.added == ["Stage · Beta"]
    assert experiences.updated == ["Data scientist · ACME"]


def test_merge_distinguishes_periods() -> None:
    current = CareerProfile(
        experiences=[Experience(title="Vendeur", organization="X", start="2022")]
    )
    incoming = CareerProfile(
        experiences=[Experience(title="Vendeur", organization="X", start="2024")]
    )
    merged, _ = merge_profiles(current, incoming)
    assert len(merged.experiences) == 2


def test_merge_skills_and_duplicate_ids() -> None:
    current = sample_profile()
    incoming = CareerProfile.model_validate(
        {
            "skills": [
                {"id": current.skills[0].id, "category": "langages", "items": ["Go", "python"]}
            ]
        }
    )
    merged, _ = merge_profiles(current, incoming)
    assert len(merged.skills) == 3
    assert merged.skills[0].items == ["Python", "SQL", "R", "Go"]
    other = CareerProfile.model_validate(
        {"projects": [{"id": current.projects[0].id, "name": "Nouveau projet"}]}
    )
    merged, _ = merge_profiles(current, other)
    ids = [p.id for p in merged.projects]
    assert len(ids) == len(set(ids)) == 3


def test_merge_second_cv_twice_adds_nothing() -> None:
    first = sample_profile()
    second = CareerProfile.model_validate(
        {
            "projects": [{"name": "Bot Discord", "achievements": ["300 utilisateurs"]}],
            "languages": [{"name": "anglais", "certificate": "TOEFL 110"}],
            "interests": ["échecs", "Escalade"],
        }
    )
    once, _ = merge_profiles(first, second)
    twice, diff = merge_profiles(once, second)
    assert twice == once
    assert not diff.has_changes
    assert len(once.projects) == 3
    assert len(once.languages) == 3
    assert once.languages[1].certificate == "TOEIC 945"
    assert once.interests == ["Course à pied", "Échecs", "Escalade"]


# --- backup ------------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["json", "yaml"])
def test_backup_round_trip(fmt: str) -> None:
    profile = sample_profile()
    text = export_profile(profile, fmt)  # type: ignore[arg-type]
    restored, warnings = parse_backup(text.encode("utf-8"), f"backup.{fmt}")
    assert restored == profile
    assert warnings == []


def test_backup_accepts_bare_profile_and_bom() -> None:
    data = json.dumps({"headline": "Titre"}).encode("utf-8-sig")
    restored, _ = parse_backup(data, "x.json")
    assert restored.headline == "Titre"
    restored, _ = parse_backup(yaml.safe_dump({"summary": "Résumé"}).encode(), "x.txt")
    assert restored.summary == "Résumé"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\xff\xfe\x00", "UTF-8"),
        (b"[1, 2]", "profil"),
        (b"key: [unclosed", "valide"),
        (b'{"format_version": 99, "profile": {}}', "plus récente"),
    ],
)
def test_backup_errors(content: bytes, message: str) -> None:
    with pytest.raises(BackupError, match=message):
        parse_backup(content, "x.json")


# --- store -------------------------------------------------------------------------------


def test_store_versions_and_conflicts(migrated_db: object) -> None:
    empty = store.get_profile()
    assert empty.version == 0
    assert not empty.profile.has_content()
    saved = store.save_profile(CareerProfile(headline="A"), expected_version=0)
    assert saved.version == 1
    assert store.save_profile(CareerProfile(headline="B"), expected_version=1).version == 2
    with pytest.raises(store.VersionConflictError) as excinfo:
        store.save_profile(CareerProfile(headline="C"), expected_version=1)
    assert excinfo.value.current_version == 2
    stored = store.get_profile()
    assert stored.profile.headline == "B"
    assert stored.updated_at is not None
    assert stored.updated_at.tzinfo is not None
