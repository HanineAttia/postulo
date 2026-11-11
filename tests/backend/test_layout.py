"""Layout quality of the CV (SPEC 16.1): grid entries, page fill, layout check, PNG, texts."""

from __future__ import annotations

import struct
from importlib import resources

import pypdfium2 as pdfium
import pytest

from postulo.services.documents import normalize
from postulo.services.documents.assemble import build_cv
from postulo.services.documents.compact import compact_cv
from postulo.services.documents.fill import fill_selection
from postulo.services.documents.model import CvDocument
from postulo.services.documents.preview_png import PNG_SIGNATURE, pdf_to_png_pages
from postulo.services.documents.render import RenderedPdf, fill_ratio, render_pdf
from postulo.services.documents.selection import SelectedItem, Selection, default_selection
from postulo.services.profile.sample import sample_profile
from postulo.services.profile.schema import CareerProfile, Experience, Project
from postulo.services.quality.layout_check import check_layout, is_fragment

OFFER = resources.files("postulo").joinpath("data/sample_offer.txt").read_text("utf-8")


@pytest.fixture
def profile() -> CareerProfile:
    return sample_profile()


def _render(doc: CvDocument) -> RenderedPdf:
    return render_pdf(doc, "cv")


def _fit(profile: CareerProfile, selection: Selection) -> tuple[CvDocument, RenderedPdf]:
    return compact_cv(build_cv(profile, selection), 1, _render)


def _first_char_box(pdf: bytes, text: str) -> tuple[float, float, float, float]:
    document = pdfium.PdfDocument(pdf)
    textpage = document[0].get_textpage()
    searcher = textpage.search(text, match_case=True)
    hit = searcher.get_next()
    assert hit is not None, text
    box: tuple[float, float, float, float] = textpage.get_charbox(hit[0], loose=True)
    return box


# --- two-column entries ---------------------------------------------------------------------


def test_long_title_and_organization_keep_the_date_on_the_first_line_right(
    profile: CareerProfile,
) -> None:
    title = (
        "Stagiaire ingénieure en science des données et apprentissage automatique appliqué "
        "à la détection de fraude"
    )
    organization = (
        "Direction de l'innovation numérique et des données du Groupe Assurance Exemple Mutuelle "
        "Nationale"
    )
    profile.experiences[0].title = title
    profile.experiences[0].organization = organization
    doc, rendered = _fit(profile, default_selection(profile))

    page_width = pdfium.PdfDocument(rendered.data)[0].get_width()
    title_box = _first_char_box(rendered.data, title[:30])
    date_box = _first_char_box(rendered.data, "avr. 2026 – août 2026")
    org_box = _first_char_box(rendered.data, organization[:30])
    # Same first line, date on the right, organization on a lower line.
    assert abs(title_box[1] - date_box[1]) < 2
    assert date_box[0] > page_width / 2
    assert org_box[1] < title_box[1] - 8
    report = check_layout(rendered.data, doc)
    assert {c.key: c.ok for c in report.checks}["dates_on_title_line"]


# --- page fill ------------------------------------------------------------------------------


def _rich(profile: CareerProfile) -> CareerProfile:
    profile.experiences.append(
        Experience(
            title="Analyste de données (job étudiant)", organization="Énergie Locale Exemple",
            city="Cergy", start="2024-07", end="2024-08",
            achievements=[
                "Construit des tableaux de bord SQL pour suivre la consommation d'électricité",
                "Automatisé un rapport Python hebdomadaire lu par 30 personnes",
            ],
            skills=["SQL", "Python"],
        )
    )  # fmt: skip
    profile.projects.append(
        Project(
            name="Détection d'anomalies sur des compteurs d'énergie",
            achievements=["Entraîné un modèle de détection d'anomalies avec scikit-learn"],
            skills=["scikit-learn", "Pandas"],
        )
    )
    return profile


@pytest.mark.parametrize("enrich", [False, True])
def test_a_rich_profile_fills_the_page_between_85_and_100_percent(
    profile: CareerProfile, enrich: bool
) -> None:
    if enrich:
        profile = _rich(profile)
    selection = default_selection(profile)
    filled = fill_selection(
        selection,
        profile,
        OFFER,
        build=lambda s: build_cv(profile, s),
        render=_render,
    )
    doc, rendered = _fit(profile, filled.selection)
    assert rendered.pages == 1
    assert 0.85 <= fill_ratio(rendered.data, doc) <= 1.0
    report = check_layout(rendered.data, doc)
    assert all(c.ok for c in report.checks), report.checks


def test_a_short_cv_gets_relevant_content_only(profile: CareerProfile) -> None:
    profile.projects.append(
        Project(name="Atelier de pâtisserie", achievements=["Préparé des tartes aux fraises"])
    )
    short = Selection(
        title="Stage data scientist",
        education=["F0"],
        experiences=[SelectedItem(ref="E0", bullets=profile.experiences[0].achievements[:1])],
        languages=["L0"],
    )
    result = fill_selection(
        short, profile, OFFER, build=lambda s: build_cv(profile, s), render=_render
    )
    assert result.added  # relevant content was added
    assert len(result.selection.experiences[0].bullets) > 1
    assert "item:P2" not in result.added  # the pastry project is unrelated to the offer
    assert all(p.ref != "P2" for p in result.selection.projects)
    assert result.selection.experiences[0].bullets[0] == profile.experiences[0].achievements[0]


def test_fill_does_not_modify_the_selection(profile: CareerProfile) -> None:
    selection = Selection(education=["F0"], languages=["L0"])
    before = selection.model_dump()
    fill_selection(selection, profile, OFFER, build=lambda s: build_cv(profile, s), render=_render)
    assert selection.model_dump() == before


# --- layout check ---------------------------------------------------------------------------


def test_layout_check_reports_bad_layouts(profile: CareerProfile) -> None:
    long = "Réalisé " + "une analyse détaillée des données de production avec les équipes " * 3
    profile.experiences[0].achievements = [long + "et un pipeline de", "RÉDIGÉ LA DOCUMENTATION"]
    profile.experiences[1].organization = ""
    profile.experiences[1].start = profile.experiences[1].end = None
    selection = default_selection(profile)
    doc, rendered = _fit(profile, selection)
    failed = {c.key for c in check_layout(rendered.data, doc).checks if not c.ok}
    assert {"bullets_max_two_lines", "no_fragments", "no_uppercase_lines",
            "entries_complete"} <= failed  # fmt: skip


def test_layout_check_reports_a_half_empty_page(profile: CareerProfile) -> None:
    selection = Selection(education=["F0"], languages=["L0"])
    doc = build_cv(profile, selection)
    report = check_layout(_render(doc).data, doc)
    fill = next(c for c in report.checks if c.key == "page_fill")
    assert not fill.ok
    assert "%" in fill.detail
    assert report.fill < 0.5


def test_fragments() -> None:
    assert is_fragment("Construit un pipeline de")
    assert is_fragment("Réduit les coûts et")
    assert is_fragment("Built a model for")
    assert not is_fragment("Réduit les coûts de 18 %")
    assert not is_fragment("Présenté les résultats au comité de direction")


# --- normalization --------------------------------------------------------------------------


def test_free_texts_are_normalized() -> None:
    assert normalize.free_text("Élève ingénieure\nen data   science", "fr") == (
        "Élève ingénieure en data science"
    )
    assert normalize.bullet("- Atteint ~95 % de précision sur 500K lignes.", "fr") == (
        "Atteint environ 95 % de précision sur 500 000 lignes"
    )
    assert normalize.bullet("Reached ~95% on 1.5K rows and 2M users.", "en") == (
        "Reached about 95% on 1,500 rows and 2 million users"
    )
    assert normalize.free_text("Budget de 1,2M d'euros", "fr") == "Budget de 1,2 million d'euros"
    assert normalize.bullet("Formé 3 personnes etc.", "fr") == "Formé 3 personnes etc."
    assert normalize.city("cergy") == "Cergy"
    assert normalize.city("SAINT-DENIS") == "Saint-Denis"
    assert normalize.city("Paris La Défense") == "Paris La Défense"
    assert (
        normalize.email_body("Bonjour,\n\n\n\nMerci  ~5K", "fr")
        == "Bonjour,\n\nMerci environ 5 000"
    )


def test_cv_texts_are_normalized_at_rendering_not_in_the_library(profile: CareerProfile) -> None:
    profile.summary = "Ligne coupée\npar l'import."
    profile.experiences[0].city = "cergy"
    profile.experiences[0].achievements[0] = "Atteint ~95 % sur 500K lignes."
    cv = build_cv(profile, default_selection(profile))
    assert cv.summary == "Ligne coupée par l'import."
    entry = next(s for s in cv.sections if s.key == "experiences").entries[0]
    assert entry.location == "Cergy"
    assert entry.bullets[0] == "Atteint environ 95 % sur 500 000 lignes"
    assert profile.experiences[0].achievements[0] == "Atteint ~95 % sur 500K lignes."


# --- PNG previews ---------------------------------------------------------------------------


def test_png_previews(profile: CareerProfile) -> None:
    _doc, rendered = _fit(profile, default_selection(profile))
    images = pdf_to_png_pages(rendered.data, scale=1.0)
    assert len(images) == 1
    png = images[0]
    assert png.startswith(PNG_SIGNATURE)
    width, height = struct.unpack(">II", png[16:24])
    assert width in (595, 596)  # A4 (595.28 pt) at 72 dpi
    assert height == 842
    assert png.endswith(b"IEND\xaeB`\x82")
