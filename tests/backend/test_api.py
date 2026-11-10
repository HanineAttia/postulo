from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from postulo import __version__
from postulo.app import create_app

pytestmark = pytest.mark.anyio


async def _client_for(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            yield client


@pytest.fixture
async def client(postulo_home: Path, tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>SPA</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    app = create_app(demo_step_seconds=0.02, frontend_dir=dist)
    async for c in _client_for(app):
        yield c


def _parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = [line for line in block.splitlines() if not line.startswith(":")]
        if not lines:
            continue
        event = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data)))
    return events


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"app": "Postulo", "version": __version__, "status": "ok"}


async def test_database_created_on_startup(client: httpx.AsyncClient, postulo_home: Path) -> None:
    assert (postulo_home / "postulo.db").is_file()


async def test_settings_round_trip(client: httpx.AsyncClient) -> None:
    initial = (await client.get("/api/settings")).json()
    assert initial["demo_mode"] is True
    assert initial["ai"]["provider"] == "mock"

    body = {"ai": initial["ai"], "ui": {**initial["ui"], "language": "en"}}
    updated = (await client.put("/api/settings", json=body)).json()
    assert updated["ui"]["language"] == "en"
    assert (await client.get("/api/settings")).json()["ui"]["language"] == "en"


async def test_settings_rejects_invalid_values(client: httpx.AsyncClient) -> None:
    response = await client.put("/api/settings", json={"ai": {"provider": "nope"}})
    assert response.status_code == 422


async def test_llm_status(client: httpx.AsyncClient) -> None:
    data = (await client.get("/api/llm/status")).json()
    assert data["provider"] == "mock"
    assert data["demo_mode"] is True
    assert data["available"] is True
    assert data["calls_today"] == 0


async def test_llm_status_unimplemented_provider(client: httpx.AsyncClient) -> None:
    await client.put("/api/settings", json={"ai": {"provider": "anthropic_api"}})
    data = (await client.get("/api/llm/status")).json()
    assert data["available"] is False
    assert data["demo_mode"] is False


async def test_demo_job_over_sse(client: httpx.AsyncClient) -> None:
    started = await client.post("/api/jobs/demo")
    assert started.status_code == 202
    job_id = started.json()["id"]

    response = await client.get(f"/api/jobs/{job_id}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names[-1] == "end"
    assert set(names[:-1]) == {"progress"}
    assert len(events) > 5
    final = events[-1][1]
    assert final["status"] == "succeeded"
    assert final["progress"] == 100

    job = (await client.get(f"/api/jobs/{job_id}")).json()
    assert job["status"] == "succeeded"
    assert (await client.get("/api/llm/status")).json()["calls_today"] == 1


async def test_unknown_job_is_404(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/jobs/nope")).status_code == 404
    assert (await client.get("/api/jobs/nope/events")).status_code == 404


async def test_spa_routes(client: httpx.AsyncClient) -> None:
    home = await client.get("/")
    assert home.status_code == 200
    assert "SPA" in home.text
    deep = await client.get("/offres/123")
    assert "SPA" in deep.text  # client-side route falls back to index.html
    asset = await client.get("/assets/app.js")
    assert asset.text == "console.log(1)"
    assert "immutable" in asset.headers["cache-control"]


async def test_unknown_api_route_is_404_not_spa(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/nothing")).status_code == 404


async def test_path_traversal_is_blocked(client: httpx.AsyncClient) -> None:
    response = await client.get("/..%2F..%2Fsecret.txt")
    assert "SPA" in response.text


async def test_foreign_host_rejected(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health", headers={"host": "evil.example"})
    assert response.status_code == 400


async def test_no_cors_outside_dev_mode(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health", headers={"origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in response.headers


async def test_cors_in_dev_mode(postulo_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTULO_DEV", "1")
    async for c in _client_for(create_app()):
        response = await c.get("/api/health", headers={"origin": "http://localhost:5173"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_frontend_missing_page(postulo_home: Path, tmp_path: Path) -> None:
    async for c in _client_for(create_app(frontend_dir=tmp_path / "missing")):
        assert "pnpm -C frontend build" in (await c.get("/")).text
