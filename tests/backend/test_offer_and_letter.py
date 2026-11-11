"""Offer metadata, slogans, keywords, e-mail signature, letter checks and jury rules (SPEC 16.2-16.3)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from importlib import resources
from pathlib import Path

import httpx
import pytest

from postulo.app import create_app
from postulo.config import Settings, save_settings
from postulo.services.documents.assemble import with_signature
from postulo.services.documents.draft import ApplicationDraft, DraftOffer
from postulo.services.documents.honesty import apply_guard, is_short_keyword
from postulo.services.documents.offer_meta import (
    OfferMetaAI,
    extract_offer_meta,
    is_slogan,
    looks_like_job_title,
    merge_ai_meta,
)
from postulo.services.llm import registry
from postulo.services.llm.providers.mock import MockProvider
from postulo.services.profile.sample import sample_profile
from postulo.services.quality.jury import RawJury, normalize_jury
from postulo.services.quality.letter_check import check_letter

OFFER = resources.files("postulo").joinpath("data/sample_offer.txt").read_text("utf-8")
SLOGAN = "Construisons ensemble un avenir de confiance"
POSITION = "Stage de fin d'études - Data scientist (H/F)"


# --- position and slogans ---------------------------------------------------------------------


def test_a_slogan_on_the_first_line_is_never_the_position() -> None:
    offer = (
        f"{SLOGAN}\n\nStage de fin d'études - Data scientist (H/F)\nEntreprise : Énergie Exemple"
    )
    meta = extract_offer_meta(offer)
    assert meta.title == POSITION
    assert meta.title_found
    assert meta.organization == "Énergie Exemple"
    assert is_slogan(SLOGAN)
    assert not looks_like_job_title(SLOGAN)


def test_no_sure_position_leaves_the_field_empty() -> None:
    meta = extract_offer_meta(f"{SLOGAN}\nNotre équipe grandit.\nVous aimez les données ?")
    assert meta.title == ""
    assert not meta.title_found


def test_slogan_hints_never_reject_a_real_job_title() -> None:
    title = "Ingénieure avenir énergétique ensemble (H/F)"
    assert looks_like_job_title(title)
    assert not is_slogan(title)
    assert extract_offer_meta(f"{SLOGAN}\n{title}\nVous serez chargé de missions.").title == title


def test_labelled_lines_and_sentences() -> None:
    offer = (
        "Rejoignez une équipe passionnée !\nIntitulé du poste : Analyste financier junior\n"
        "Lieu : Lyon (69), hybride\nVous serez chargée de la consolidation."
    )
    meta = extract_offer_meta(offer)
    assert meta.title == "Analyste financier junior"
    assert meta.city == "Lyon"
    assert extract_offer_meta("Rejoignez-nous en tant que Développeuse back-end (F/H) !").title == (
        "Développeuse back-end (F/H)"
    )


def test_the_ai_position_is_used_only_if_it_is_a_job_title_in_the_offer() -> None:
    offer = (
        f"{SLOGAN}\nPoste à pourvoir chez Énergie Exemple, à Paris.\nData scientist junior (H/F)"
    )
    rules = extract_offer_meta(offer)
    slogan = merge_ai_meta(rules, OfferMetaAI(title=SLOGAN, organization="Énergie Exemple"), offer)
    assert slogan.title == rules.title
    assert slogan.organization == "Énergie Exemple"
    invented = merge_ai_meta(rules, OfferMetaAI(title="Lead data scientist", city="Lille"), offer)
    assert invented.title == rules.title  # not in the offer
    assert invented.city == ""  # not in the offer
    real = merge_ai_meta(rules, OfferMetaAI(title="Data scientist junior (H/F)"), offer)
    assert real.title == "Data scientist junior (H/F)"
    assert real.source == "ai"


# --- keywords ---------------------------------------------------------------------------------


def test_offer_keywords_are_short_and_never_languages() -> None:
    assert is_short_keyword("Python")
    assert is_short_keyword("séries temporelles")
    assert is_short_keyword("Node.js")
    assert not is_short_keyword("Anglais")
    assert not is_short_keyword("Anglais professionnel")
    assert not is_short_keyword("Une première expérience avec Spark ou un cloud public")
    draft = ApplicationDraft(
        offer=DraftOffer(keywords=["Python", "Anglais professionnel", "machine learning", "SQL."])
    )
    assert apply_guard(draft, sample_profile(), OFFER).keywords == ["Python", "machine learning"]


# --- e-mail signature (correction a) ----------------------------------------------------------


def test_the_server_signs_the_email_from_the_profile() -> None:
    profile = sample_profile()
    body = (
        "Madame, Monsieur,\n\nMa candidature.\n\nBien cordialement,\n[Prénom Nom]\n06 12 34 56 78"
    )
    signed = with_signature(body, profile, "fr")
    assert signed.endswith(
        "Bien cordialement,\nCamille Exemple\n+33 6 00 00 00 00\n"
        "https://www.linkedin.com/in/camille-exemple-fictif"
    )
    assert "[" not in signed
    assert "06 12" not in signed
    profile.identity.phone = None
    profile.identity.linkedin = None
    assert with_signature("Hello,\n\nMy application.", profile, "en").endswith(
        "Kind regards,\nCamille Exemple"
    )


# --- letter checks ----------------------------------------------------------------------------

GOOD_LETTER = [
    f"Votre offre « {POSITION} » chez Énergie Exemple a retenu mon attention : développer des "
    "modèles de machine learning pour prévoir la consommation d'électricité, et détecter les "
    "anomalies et les fraudes sur les relevés de compteurs.",
    "Chez Assurance Exemple, j'ai augmenté le rappel d'un modèle de détection de fraude de 18 %.",
    "J'aimerais en parler avec vous lors d'un entretien.",
]


def test_a_good_letter_passes() -> None:
    assert (
        check_letter(
            GOOD_LETTER, offer_text=OFFER, organization="Énergie Exemple", position=POSITION
        )
        == []
    )


def test_letter_problems_are_reported() -> None:
    bad = [
        "Votre organisation porte une belle idée : « Construisons ensemble un avenir "
        "énergétique de confiance ».",
        "J'ai travaillé grâce à un pipeline de et assistant client sur des sujets variés.",
        "Je reste disponible pour un échange...",
    ]
    warnings = check_letter(
        bad, offer_text=OFFER, organization="Énergie Exemple", position=POSITION
    )
    text = " ".join(warnings)
    assert "ne nomme pas l'organisation" in text
    assert "intitulé exact" in text
    assert "moins de deux éléments concrets" in text
    assert "slogan" in text
    assert "pipeline de et assistant" in text
    assert "échange..." in text or "Je reste disponible" in text


# --- jury rule by rule ------------------------------------------------------------------------


def test_jury_rules_and_rule_ids_are_normalized() -> None:
    raw = RawJury.model_validate(
        {
            "score": 70,
            "rules": [
                {"id": "r-2", "ok": False, "comment": "Peu de chiffres"},
                {"id": "R-99", "ok": True},
                {"id": "R02", "ok": True},
            ],
            "corrections": [{"priority": "high", "rule": "R2", "text": "Chiffrer."}],
        }
    )
    report = normalize_jury(raw)
    assert [(r.id, r.ok) for r in report.rules] == [("R-02", False)]
    assert report.corrections[0].rule == "R-02"


# --- API --------------------------------------------------------------------------------------


@pytest.fixture
async def client(postulo_home: Path) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(demo_step_seconds=0.0, frontend_dir=None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            yield c


@pytest.mark.anyio
async def test_analyze_offer_in_demo_mode_uses_the_rules(client: httpx.AsyncClient) -> None:
    body = (await client.post("/api/applications/analyze-offer", json={"offer_text": OFFER})).json()
    assert body["title"] == POSITION
    assert body["organization"] == "Énergie Exemple"
    assert body["city"] == "Paris"
    assert body["source"] == "rules"
    vague = f"{SLOGAN}\n" + "Notre équipe grandit et cherche de nouveaux talents. " * 3
    empty = (
        await client.post("/api/applications/analyze-offer", json={"offer_text": vague})
    ).json()
    assert empty["title"] == ""
    assert empty["title_found"] is False


@pytest.mark.anyio
async def test_analyze_offer_with_a_provider_keeps_only_values_from_the_offer(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_settings(Settings.model_validate({"ai": {"provider": "claude_code_cli"}}))
    answer = '{"title": "%s", "organization": "Énergie Exemple", "city": "Paris", ' % SLOGAN
    answer += '"keywords": ["Python", "Anglais"]}'
    monkeypatch.setattr(
        registry, "get_provider", lambda _s=None: MockProvider({"offer_meta": answer})
    )
    body = (await client.post("/api/applications/analyze-offer", json={"offer_text": OFFER})).json()
    assert body["title"] == POSITION  # the slogan proposed by the AI is refused
    assert body["organization"] == "Énergie Exemple"


@pytest.mark.anyio
async def test_generation_needs_a_position(client: httpx.AsyncClient) -> None:
    await client.post("/api/profile/sample", json={})
    vague = f"{SLOGAN}\n" + "Notre équipe grandit et cherche de nouveaux talents. " * 3
    response = await client.post("/api/applications", json={"offer_text": vague})
    assert response.status_code == 422
    assert "intitulé exact du poste" in response.json()["detail"]
