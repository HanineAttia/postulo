"""ATS check, jury, workshop pipeline and API (SPEC 7.6, 12.3; acceptance of SPEC 14 phase 2)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from importlib import resources
from pathlib import Path
from typing import Any

import httpx
import pytest

from postulo.app import create_app
from postulo.services.documents.assemble import build_cv
from postulo.services.documents.compact import compact_cv
from postulo.services.documents.model import CvDocument
from postulo.services.documents.preview_png import PNG_SIGNATURE
from postulo.services.documents.render import RenderedPdf, render_pdf
from postulo.services.documents.selection import default_selection
from postulo.services.llm.usage import calls_today
from postulo.services.profile.sample import sample_profile
from postulo.services.profile.schema import CareerProfile
from postulo.services.quality import ats_check
from postulo.services.quality.ats_check import check_cv_pdf
from postulo.services.quality.jury import RawJury, normalize_jury, normalize_score

OFFER = resources.files("postulo").joinpath("data/sample_offer.txt").read_text("utf-8")


@pytest.fixture
def profile() -> CareerProfile:
    return sample_profile()


def _cv_pdf(profile: CareerProfile) -> tuple[bytes, list[str]]:
    cv, rendered = compact_cv(build_cv(profile, default_selection(profile)), 1, _render)
    return rendered.data, [s.title for s in cv.sections]


def _render(doc: CvDocument) -> RenderedPdf:
    return render_pdf(doc, "cv")


# --- ATS check --------------------------------------------------------------------------------


def test_ats_check_passes_on_a_generated_cv(profile: CareerProfile) -> None:
    pdf, headings = _cv_pdf(profile)
    report = check_cv_pdf(
        pdf, profile=profile, keywords=["Python", "scikit-learn", "Spark"],
        target_pages=1, headings=headings,
    )  # fmt: skip
    failed = [c for c in report.checks if not c.ok]
    assert failed == []
    assert report.checks_score == 100
    assert report.keywords_found == ["Python", "scikit-learn"]
    assert report.keywords_missing == ["Spark"]
    assert report.coverage == 67
    assert report.score == round(0.6 * 100 + 0.4 * 67)
    assert report.text.startswith("Camille Exemple")


def test_ats_check_without_keywords_uses_checks_only(profile: CareerProfile) -> None:
    pdf, headings = _cv_pdf(profile)
    report = check_cv_pdf(pdf, profile=profile, keywords=[], target_pages=1, headings=headings)
    assert report.coverage is None
    assert report.score == report.checks_score == 100


def test_ats_check_detects_missing_contact_and_links(profile: CareerProfile) -> None:
    other = profile.model_copy(deep=True)
    other.identity.email = "autre@example.com"
    other.identity.portfolio = "https://camille.example.com"
    pdf, headings = _cv_pdf(profile)
    report = check_cv_pdf(pdf, profile=other, keywords=[], target_pages=1, headings=headings)
    failed = {c.key: c.detail for c in report.checks if not c.ok}
    assert set(failed) == {"email_readable", "links_clickable"}
    assert "https://camille.example.com" in failed["links_clickable"]


def test_ats_check_detects_bad_characters_ligatures_and_pages(
    profile: CareerProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf, headings = _cv_pdf(profile)
    real_text, _pages = ats_check.extract_text(pdf)
    monkeypatch.setattr(
        ats_check, "extract_text", lambda _pdf: ("Intro\n" + real_text + " ﬁ � ", 2)
    )
    report = check_cv_pdf(pdf, profile=profile, keywords=[], target_pages=1, headings=headings)
    failed = {c.key for c in report.checks if not c.ok}
    assert failed == {"no_ligatures", "no_bad_characters", "page_count", "name_first_line"}


# --- jury normalization -----------------------------------------------------------------------


def test_jury_score_on_ten_is_normalized() -> None:
    criteria = dict.fromkeys(("fit", "impact", "clarity"), 8.0)
    assert normalize_score(8.4, criteria) == 84
    assert normalize_score(8.4, {}) == 84
    assert normalize_score(78, criteria) == 78
    assert normalize_score(8, dict.fromkeys(("fit", "impact"), 2.0)) == 8  # incoherent: on 100
    assert normalize_score(140, criteria) == 100


def test_jury_report_is_normalized() -> None:
    raw = RawJury.model_validate(
        {
            "score": "7.5",
            "decision": "Peut-être",
            "criteria": {"fit": 80, "impact": "7", "clarity": "x", "letter": -3},
            "corrections": [
                {"priority": "basse", "target": "Letter", "text": "b"},
                {"priority": "Haute", "target": "", "text": "a"},
                {"priority": "high", "text": "  "},
            ],
        }
    )
    report = normalize_jury(raw)
    assert report.score == 75
    assert report.decision == "maybe"
    assert report.criteria == {"fit": 8.0, "impact": 7.0, "letter": 0.0}
    assert [(c.priority, c.target, c.text) for c in report.corrections] == [
        ("high", "cv", "a"),
        ("low", "letter", "b"),
    ]


# --- pipeline through the API (demo mode) -----------------------------------------------------


@pytest.fixture
async def client(postulo_home: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(demo_step_seconds=0.0, frontend_dir=None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            yield c


async def _wait(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    job: dict[str, Any] = {}
    for _ in range(600):
        job = (await client.get(f"/api/jobs/{job_id}")).json()
        if job["status"] not in ("pending", "running"):
            break
        await asyncio.sleep(0.02)
    return job


async def _generate(client: httpx.AsyncClient, **options: Any) -> dict[str, Any]:
    started = await client.post("/api/applications", json={"offer_text": OFFER, **options})
    assert started.status_code == 202, started.text
    job = await _wait(client, started.json()["id"])
    assert job["status"] == "succeeded", job
    assert [s["status"] for s in job["steps"]] == ["done"] * 5
    detail: dict[str, Any] = (
        await client.get(f"/api/applications/{job['result']['application_id']}")
    ).json()
    return detail


@pytest.mark.anyio
async def test_refuses_empty_profile_and_short_offer(client: httpx.AsyncClient) -> None:
    short = await client.post("/api/applications", json={"offer_text": "Stage data"})
    assert short.status_code == 422
    empty = await client.post("/api/applications", json={"offer_text": OFFER})
    assert empty.status_code == 409
    assert "parcours est vide" in empty.json()["detail"]


@pytest.mark.anyio
async def test_full_pipeline_in_demo_mode(client: httpx.AsyncClient, postulo_home: Path) -> None:
    """SPEC 14 phase 2 acceptance on the sample profile, in demo mode."""
    assert (await client.post("/api/profile/sample", json={})).status_code == 200
    detail = await _generate(client)
    report = detail["report"]

    # One page, clickable links, no ligature, ATS >= 85, jury before and after.
    assert report["pages"] == 1
    checks = {c["key"]: c["ok"] for c in report["ats"]["checks"]}
    assert checks["links_clickable"]
    assert checks["no_ligatures"]
    assert all(checks.values()), report["ats"]["checks"]
    assert report["ats"]["score"] >= 85
    assert detail["jury_score_before"] == 74
    assert detail["jury_score_after"] == 84
    assert report["revision_applied"]
    assert report["revision_kept"]
    assert report["jury_after"]["decision"] == "interview"

    assert detail["organization"] == "Énergie Exemple"
    assert detail["status"] == "draft"
    assert "[" not in detail["email_body"]
    assert "Camille Exemple" in detail["email_body"]
    assert report["cv_file"] == "CV_Camille-Exemple_Energie-Exemple.pdf"
    assert report["letter_file"] == "Lettre_Camille-Exemple_Energie-Exemple.pdf"

    folder = postulo_home / "applications" / detail["id"]
    names = {p.name for p in folder.iterdir()}
    assert {"offer.txt", "draft.json", "revised_draft.json", "documents.json", "data.json",
            "report.json", report["cv_file"], report["letter_file"]} <= names  # fmt: skip

    pdf = await client.get(detail["files"]["cv"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.headers["content-disposition"].startswith("inline")
    assert pdf.content.startswith(b"%PDF")
    download = await client.get(detail["files"]["letter"], params={"download": "true"})
    assert download.headers["content-disposition"].startswith("attachment")

    listing = (await client.get("/api/applications")).json()
    assert [a["id"] for a in listing] == [detail["id"]]

    # SPEC 16: the position, never the slogan of the first line; complete layout; images.
    position = "Stage de fin d'études - Data scientist (H/F)"
    assert detail["position"] == position
    assert detail["documents"]["cv"]["title"] == position
    assert "Construisons" not in detail["documents"]["cv"]["title"]
    assert detail["documents"]["letter"]["subject"].endswith("Candidature – " + position)
    assert detail["email_subject"] == "Candidature – " + position
    assert detail["report"]["warnings"] == []
    assert all(c["ok"] for c in report["layout"]["checks"]), report["layout"]
    assert 0.85 <= report["layout"]["fill"] <= 1.0
    assert detail["email_body"].endswith(
        "Bien cordialement,\nCamille Exemple\n+33 6 00 00 00 00\n"
        "https://www.linkedin.com/in/camille-exemple-fictif"
    )
    assert report["jury_before"]["rules"]
    assert detail["previews"]["cv"] == [f"/api/applications/{detail['id']}/files/cv/preview/1"]
    image = await client.get(detail["previews"]["letter"][0])
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(PNG_SIGNATURE)


@pytest.mark.anyio
async def test_without_jury_and_in_english(client: httpx.AsyncClient) -> None:
    await client.post("/api/profile/sample", json={})
    detail = await _generate(client, jury=False, lang="en", template="classic")
    assert detail["jury_score_before"] is None
    assert detail["report"]["revision_applied"] is False
    sections = [s["title"] for s in detail["documents"]["cv"]["sections"]]
    assert "Experience" in sections
    assert "Education" in sections
    assert detail["documents"]["cv"]["layout"]["template"] == "classic"
    assert detail["report"]["letter_file"].startswith("Letter_")


@pytest.mark.anyio
async def test_edit_and_regenerate_without_ai(client: httpx.AsyncClient) -> None:
    await client.post("/api/profile/sample", json={})
    detail = await _generate(client, jury=False)
    calls_before = calls_today()

    documents = detail["documents"]
    documents["cv"]["summary"] = "Accroche modifiée à la main, R&D 50% #1."
    documents["cv"]["layout"]["template"] = "classic"
    documents["letter"]["paragraphs"][0] = "Paragraphe réécrit."
    response = await client.put(
        f"/api/applications/{detail['id']}/documents",
        json={"documents": documents, "email_subject": "Objet", "email_body": "Corps"},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert calls_today() == calls_before  # no AI call
    assert updated["report"]["edited"] is True
    assert "Accroche modifiée à la main, R&D 50% #1." in updated["report"]["ats"]["text"]
    assert updated["documents"]["cv"]["layout"]["font"] == "Source Serif 4"
    assert updated["documents"]["letter"]["layout"]["template"] == "classic"
    assert updated["email_subject"] == "Objet"
    assert updated["report"]["ats_before"] is not None


@pytest.mark.anyio
async def test_mark_sent_and_not_found(client: httpx.AsyncClient) -> None:
    await client.post("/api/profile/sample", json={})
    detail = await _generate(client, jury=False)
    sent = (await client.post(f"/api/applications/{detail['id']}/sent")).json()
    assert sent["status"] == "sent"
    assert sent["sent_at"] is not None
    assert (await client.get("/api/applications/unknown")).status_code == 404
    assert (await client.get(f"/api/applications/{detail['id']}/files/other")).status_code == 422


@pytest.mark.anyio
async def test_sample_offer(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/applications/sample-offer")).json()
    assert "Énergie Exemple" in body["text"]
