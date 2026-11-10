"""HTTP API of the career library."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from postulo.app import create_app
from postulo.services.profile.sample import sample_profile

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client(postulo_home: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(demo_step_seconds=0.01, frontend_dir=None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            yield c


async def _load_sample(client: httpx.AsyncClient) -> dict[str, Any]:
    response = await client.post("/api/profile/sample", json={})
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


async def test_empty_profile_then_save(client: httpx.AsyncClient) -> None:
    initial = (await client.get("/api/profile")).json()
    assert initial["version"] == 0
    assert initial["profile"]["experiences"] == []
    profile = initial["profile"]
    profile["headline"] = "Data scientist"
    profile["experiences"] = [{"title": "Stage", "start": "2026/4", "achievements": ["A", " "]}]
    saved = await client.put("/api/profile", json={"version": 0, "profile": profile})
    assert saved.status_code == 200
    body = saved.json()
    assert body["version"] == 1
    assert body["profile"]["experiences"][0]["start"] == "2026-04"
    assert body["profile"]["experiences"][0]["achievements"] == ["A"]
    assert body["profile"]["experiences"][0]["id"]


async def test_save_conflict_and_validation(client: httpx.AsyncClient) -> None:
    await _load_sample(client)
    conflict = await client.put("/api/profile", json={"version": 0, "profile": {}})
    assert conflict.status_code == 409
    assert "Recharge" in conflict.json()["detail"]
    invalid = await client.put(
        "/api/profile", json={"version": 1, "profile": {"identity": {"email": "x"}}}
    )
    assert invalid.status_code == 422


async def test_sample_requires_force_when_profile_exists(client: httpx.AsyncClient) -> None:
    await _load_sample(client)
    refused = await client.post("/api/profile/sample", json={})
    assert refused.status_code == 409
    forced = await client.post("/api/profile/sample", json={"force": True})
    assert forced.status_code == 200
    assert forced.json()["version"] == 2


async def test_completeness(client: httpx.AsyncClient) -> None:
    empty = (await client.get("/api/profile/completeness")).json()
    assert empty["score"] == 0
    assert empty["advice"][0]["section"]
    await _load_sample(client)
    full = (await client.get("/api/profile/completeness")).json()
    assert full["score"] >= 90


@pytest.mark.parametrize("fmt", ["json", "yaml"])
async def test_export_and_restore(client: httpx.AsyncClient, fmt: str) -> None:
    await _load_sample(client)
    exported = await client.get(f"/api/profile/export?format={fmt}")
    assert exported.status_code == 200
    assert f".{fmt}" in exported.headers["content-disposition"]
    assert "Camille" in exported.text

    preview = await client.post(
        "/api/profile/import-backup", files={"file": (f"backup.{fmt}", exported.content)}
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["base_version"] == 1
    assert body["warnings"] == []
    experiences = next(s for s in body["merge_diff"]["sections"] if s["section"] == "experiences")
    assert experiences["added"] == []
    assert experiences["unchanged"] == 2

    applied = await client.post(
        "/api/profile/apply",
        json={"mode": "merge", "incoming": body["incoming"], "version": body["base_version"]},
    )
    assert applied.status_code == 200
    assert len(applied.json()["profile"]["experiences"]) == 2


async def test_apply_replace_and_merge(client: httpx.AsyncClient) -> None:
    sample = await _load_sample(client)
    incoming = {"headline": "Nouveau titre", "projects": [{"name": "Projet X"}]}
    merged = await client.post(
        "/api/profile/apply", json={"mode": "merge", "incoming": incoming, "version": 1}
    )
    assert merged.status_code == 200
    merged_profile = merged.json()["profile"]
    assert merged_profile["headline"] == sample["profile"]["headline"]  # kept
    assert len(merged_profile["projects"]) == 3

    replaced = await client.post(
        "/api/profile/apply", json={"mode": "replace", "incoming": incoming, "version": 2}
    )
    assert replaced.json()["profile"]["headline"] == "Nouveau titre"
    assert replaced.json()["profile"]["experiences"] == []

    stale = await client.post(
        "/api/profile/apply", json={"mode": "merge", "incoming": incoming, "version": 1}
    )
    assert stale.status_code == 409


async def test_import_backup_errors(client: httpx.AsyncClient) -> None:
    bad = await client.post("/api/profile/import-backup", files={"file": ("x.json", b"[1]")})
    assert bad.status_code == 422
    assert "profil" in bad.json()["detail"]
    warned = await client.post(
        "/api/profile/import-backup",
        files={"file": ("x.json", json.dumps({"identity": {"email": "nope"}}).encode())},
    )
    assert warned.status_code == 200
    assert len(warned.json()["warnings"]) == 1


def test_sample_ids_are_fresh() -> None:
    assert sample_profile().experiences[0].id != sample_profile().experiences[0].id
