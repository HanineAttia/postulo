"""Application workshop pipeline (docs/SPEC.md section 7).

Job steps: draft -> layout -> ats_check -> jury -> revision.
- draft: one AI call writes the whole application (draft.py);
- layout: honesty guard, assembly, rendering, compaction (no AI);
- ats_check: text extraction and checks (no AI);
- jury: one AI call on the text the ATS extracted;
- revision: below the threshold, one AI call revises the *original* draft with
  the critique and the ATS report, then layout, ATS check and jury run again.
  Only one revision. The better of the two versions is kept; both scores are shown.

`render_documents` is also used to regenerate the PDFs after an edit, without AI.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlmodel import Session

from postulo.db.models import Application, utcnow
from postulo.db.session import get_engine
from postulo.services.documents import normalize
from postulo.services.documents.assemble import (
    build_cv,
    build_letter,
    document_filename,
    fill_placeholders,
    french_typography,
)
from postulo.services.documents.compact import compact_cv, compact_letter
from postulo.services.documents.draft import (
    ApplicationDraft,
    build_draft_prompt,
    build_revision_prompt,
    merge_revision,
    sanitize_offer,
)
from postulo.services.documents.fill import fill_selection
from postulo.services.documents.honesty import GuardResult, apply_guard, letter_warnings
from postulo.services.documents.model import (
    CvDocument,
    DocLang,
    EngineName,
    LetterDocument,
    Paper,
    TemplateName,
    layout_for,
)
from postulo.services.documents.preview_png import pdf_to_png_pages
from postulo.services.documents.render import RenderedPdf, document_data, render_pdf
from postulo.services.documents.selection import Selection, limits_for
from postulo.services.jobs import JobContext, JobFunc
from postulo.services.llm.base import LLMProvider
from postulo.services.llm.json_utils import complete_json
from postulo.services.profile.schema import CareerProfile
from postulo.services.quality.ats_check import AtsReport, check_cv_pdf, extract_text
from postulo.services.quality.jury import JuryReport, run_jury
from postulo.services.quality.layout_check import LayoutReport, check_layout
from postulo.services.workshop.storage import (
    ApplicationReport,
    EditableDocuments,
    application_dir,
    read_report,
    write_json,
)

APPLICATION_JOB_TYPE = "application"
APPLICATION_STEPS = ("draft", "layout", "ats_check", "jury", "revision")


@dataclass(frozen=True)
class WorkshopOptions:
    lang: DocLang = "fr"
    template: TemplateName = "modern"
    engine: EngineName = "typst"
    jury: bool = True
    revision: bool = True
    threshold: int = 82
    organization: str = ""
    position: str = ""
    offer_city: str = ""
    paper: Paper = "a4"


@dataclass
class Rendered:
    cv: CvDocument  # compacted
    cv_pdf: RenderedPdf
    letter: LetterDocument
    letter_pdf: RenderedPdf
    ats: AtsReport
    layout: LayoutReport


@dataclass
class Produced:
    guard: GuardResult
    documents: EditableDocuments
    rendered: Rendered
    organization: str
    position: str
    email_subject: str
    email_body: str
    warnings: list[str] = field(default_factory=list)


def render_documents(
    documents: EditableDocuments,
    *,
    profile: CareerProfile,
    keywords: list[str],
    engine: EngineName,
) -> Rendered:
    """Compact and render both documents, then run the ATS check. No AI involved."""
    target = limits_for(profile).pages
    cv, cv_pdf = compact_cv(documents.cv, target, lambda d: render_pdf(d, "cv", engine))
    letter, letter_pdf = compact_letter(documents.letter, lambda d: render_pdf(d, "letter", engine))
    ats = check_cv_pdf(
        cv_pdf.data,
        profile=profile,
        keywords=keywords,
        target_pages=target,
        headings=[s.title for s in cv.sections],
    )
    layout = check_layout(cv_pdf.data, cv, target_pages=target)
    return Rendered(
        cv=cv, cv_pdf=cv_pdf, letter=letter, letter_pdf=letter_pdf, ats=ats, layout=layout
    )


def produce(
    draft: ApplicationDraft, profile: CareerProfile, offer_text: str, options: WorkshopOptions
) -> Produced:
    guard = apply_guard(draft, profile, offer_text)
    organization = options.organization.strip() or draft.offer.organization.strip()
    position = options.position.strip() or draft.offer.title.strip() or guard.selection.title

    def build(selection: Selection) -> CvDocument:
        return build_cv(
            profile, selection, lang=options.lang, template=options.template, paper=options.paper
        )

    target = limits_for(profile).pages
    selection = guard.selection
    if target == 1:
        # SPEC 16.1: a short page gets relevant library content before more spacing.
        selection = fill_selection(
            selection,
            profile,
            offer_text,
            build=build,
            render=lambda doc: render_pdf(doc, "cv", options.engine),
        ).selection
    cv = build(selection)
    letter = build_letter(
        profile,
        [fill_placeholders(p, profile, organization=organization, role=position)
         for p in draft.letter.paragraphs],
        organization=organization,
        position=position,
        offer_city=options.offer_city,
        lang=options.lang,
        template=options.template,
        paper=options.paper,
    )  # fmt: skip
    warnings = [*guard.warnings, *letter_warnings(letter.paragraphs, profile, offer_text)]
    if not letter.paragraphs:
        warnings.append("L'IA n'a pas rédigé de lettre : complète-la avec « Éditer ».")
    # Built here from the validated position, never from the AI (no slogan, no "Objet :").
    email_subject = (
        normalize.one_line(
            ("Candidature – " if options.lang == "fr" else "Application – ") + position
        )
        if position
        else normalize.one_line(draft.email.subject)
    )
    email_body = normalize.email_body(
        fill_placeholders(draft.email.body, profile, organization=organization, role=position),
        options.lang,
    )
    if options.lang == "fr":
        email_subject, email_body = french_typography(email_subject), french_typography(email_body)
    documents = EditableDocuments(cv=cv, letter=letter)
    rendered = render_documents(
        documents, profile=profile, keywords=guard.keywords, engine=options.engine
    )
    if rendered.ats.pages > limits_for(profile).pages:
        warnings.append(
            f"Le CV fait {rendered.ats.pages} pages malgré le compactage : retire un élément "
            "avec « Éditer »."
        )
    return Produced(
        guard=guard,
        documents=documents,
        rendered=rendered,
        organization=organization,
        position=position,
        email_subject=email_subject,
        email_body=email_body,
        warnings=warnings,
    )


def letter_text(letter: LetterDocument) -> str:
    return "\n\n".join([letter.subject, letter.salutation, *letter.paragraphs, letter.closing])


def save_rendered(
    folder: Path, rendered: Rendered, profile: CareerProfile, organization: str
) -> tuple[str, str]:
    cv_file = document_filename("CV", profile, organization)
    letter_kind = "Lettre" if rendered.letter.lang == "fr" else "Letter"
    letter_file = document_filename(letter_kind, profile, organization)
    for old in folder.glob("*.pdf"):
        if old.name not in (cv_file, letter_file):
            old.unlink()
    for old_png in folder.glob("*.png"):
        old_png.unlink()
    (folder / cv_file).write_bytes(rendered.cv_pdf.data)
    (folder / letter_file).write_bytes(rendered.letter_pdf.data)
    # SPEC 16.1: an image of every page, for the visual review before sending.
    for kind, pdf in (("cv", rendered.cv_pdf.data), ("letter", rendered.letter_pdf.data)):
        for number, png in enumerate(pdf_to_png_pages(pdf), start=1):
            (folder / f"{kind}-{number}.png").write_bytes(png)
    write_json(folder, "data.json", document_data(rendered.cv))
    return cv_file, letter_file


def make_application_job(
    *,
    application_id: str,
    profile: CareerProfile,
    offer_text: str,
    options: WorkshopOptions,
    provider: LLMProvider,
    timeout: int = 300,
) -> JobFunc:
    async def run(ctx: JobContext) -> dict[str, Any]:
        folder = application_dir(application_id)

        ctx.start_step("draft")
        offer, offer_warnings = sanitize_offer(offer_text)
        (folder / "offer.txt").write_text(offer, encoding="utf-8")
        draft = await complete_json(
            provider,
            build_draft_prompt(profile, offer, options.lang),
            ApplicationDraft,
            timeout=timeout,
        )
        write_json(folder, "draft.json", draft)
        ctx.finish_step("draft", progress=30)

        ctx.start_step("layout")
        produced = await asyncio.to_thread(produce, draft, profile, offer, options)
        ctx.finish_step("layout", progress=45)

        ctx.start_step("ats_check")  # done by produce(); kept as a visible step
        ctx.finish_step("ats_check", progress=55)

        ctx.start_step("jury")
        jury_before: JuryReport | None = None
        if options.jury:
            jury_before = await _jury(provider, produced, offer, options, 1, timeout)
        ctx.finish_step("jury", progress=70)

        ctx.start_step("revision")
        final, final_draft = produced, draft
        jury_after: JuryReport | None = None
        revision_applied = False
        if jury_before is not None and options.revision and jury_before.score < options.threshold:
            prompt = build_revision_prompt(
                profile,
                offer,
                options.lang,
                draft,  # the original draft, never the guarded one (lesson 5)
                jury_before.model_dump(),
                produced.rendered.ats.summary_for_prompt(),
            )
            revised = await complete_json(provider, prompt, ApplicationDraft, timeout=timeout)
            merged = merge_revision(draft, revised)
            write_json(folder, "revised_draft.json", merged)
            ctx.set_progress(80)
            second = await asyncio.to_thread(produce, merged, profile, offer, options)
            ctx.set_progress(88)
            jury_after = await _jury(provider, second, offer, options, 2, timeout)
            revision_applied = True
            if jury_after.score >= jury_before.score:
                final, final_draft = second, merged
        ctx.finish_step("revision", progress=97)

        warnings = list(offer_warnings) + final.warnings
        if revision_applied and final is produced:
            warnings.append(
                "La révision n'a pas amélioré la note du jury : la première version est gardée."
            )
        cv_file, letter_file = save_rendered(folder, final.rendered, profile, final.organization)
        write_json(folder, "documents.json", final.documents)
        report = ApplicationReport(
            warnings=warnings,
            keywords=final.guard.keywords,
            removed_skills=final.guard.removed_skills,
            tips=final_draft.tips,
            gaps=final_draft.gaps,
            ats_before=produced.rendered.ats if revision_applied else None,
            ats=final.rendered.ats,
            jury_before=jury_before,
            jury_after=jury_after,
            revision_applied=revision_applied,
            revision_kept=revision_applied and final is not produced,
            compaction_level=final.rendered.cv.layout.level,
            pages=final.rendered.ats.pages,
            target_pages=limits_for(profile).pages,
            letter_pages=final.rendered.letter_pdf.pages,
            layout=final.rendered.layout,
            engine=options.engine,
            cv_file=cv_file,
            letter_file=letter_file,
        )
        write_json(folder, "report.json", report)
        with Session(get_engine()) as session:
            session.add(
                Application(
                    id=application_id,
                    organization=final.organization,
                    position=final.position,
                    lang=options.lang,
                    template=options.template,
                    engine=options.engine,
                    folder=str(folder),
                    email_subject=final.email_subject,
                    email_body=final.email_body,
                    ats_score=final.rendered.ats.score,
                    jury_score_before=jury_before.score if jury_before else None,
                    jury_score_after=jury_after.score if jury_after else None,
                    compaction_level=final.rendered.cv.layout.level,
                    job_id=ctx.job_id,
                )
            )
            session.commit()
        return {"application_id": application_id}

    return run


async def _jury(
    provider: LLMProvider,
    produced: Produced,
    offer: str,
    options: WorkshopOptions,
    round_number: int,
    timeout: int,
) -> JuryReport:
    cv_text, _pages = extract_text(produced.rendered.cv_pdf.data)  # what the ATS sees
    return await run_jury(
        provider,
        cv_text=cv_text,
        letter_text=letter_text(produced.rendered.letter),
        offer_text=offer,
        lang=options.lang,
        round_number=round_number,
        timeout=timeout,
    )


def regenerate(
    application: Application,
    documents: EditableDocuments,
    *,
    profile: CareerProfile,
    email_subject: str,
    email_body: str,
) -> ApplicationReport:
    """Re-render edited documents and re-run the ATS check, without any AI call.

    The template of the CV applies to both documents; compaction starts again from level 0.
    """
    template = documents.cv.layout.template
    paper = documents.cv.layout.paper
    documents = EditableDocuments(
        cv=documents.cv.model_copy(update={"layout": layout_for(template, paper)}),
        letter=documents.letter.model_copy(update={"layout": layout_for(template, paper)}),
    )
    folder = Path(application.folder)
    report = read_report(folder)
    engine: EngineName = "html" if application.engine == "html" else "typst"
    rendered = render_documents(documents, profile=profile, keywords=report.keywords, engine=engine)
    cv_file, letter_file = save_rendered(folder, rendered, profile, application.organization)
    write_json(folder, "documents.json", documents)
    if report.ats_before is None:
        report.ats_before = report.ats
    report.ats = rendered.ats
    report.compaction_level = rendered.cv.layout.level
    report.pages = rendered.ats.pages
    report.letter_pages = rendered.letter_pdf.pages
    report.layout = rendered.layout
    report.cv_file, report.letter_file = cv_file, letter_file
    report.edited = True
    write_json(folder, "report.json", report)
    with Session(get_engine()) as session:
        row = session.get(Application, application.id)
        if row is not None:
            row.email_subject = email_subject
            row.email_body = email_body
            row.ats_score = rendered.ats.score
            row.compaction_level = rendered.cv.layout.level
            row.template = documents.cv.layout.template
            row.updated_at = utcnow()
            session.add(row)
            session.commit()
    return report
