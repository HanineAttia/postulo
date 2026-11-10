import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import type { ApplicationDetail, ApplicationSummary, JuryReport, SettingsRead } from "@/lib/api";
import { DEMO_STATUS, FakeEventSource, makeJob, mockApi, renderApp } from "@/test/utils";

const SETTINGS: SettingsRead = {
  ai: { provider: "mock", model: null, timeout_seconds: 300 },
  ui: { language: "fr", theme: "system" },
  documents: {
    engine: "typst",
    template: "classic",
    language: "fr",
    jury: true,
    revision: true,
    threshold: 82,
  },
  onboarding_completed: true,
  demo_mode: true,
};

const OFFER = "Stage data scientist chez Énergie Exemple. ".repeat(4);

function jury(score: number, decision: JuryReport["decision"]): JuryReport {
  return {
    score,
    decision,
    six_second_impression: "Profil clair.",
    criteria: { fit: 8, impact: 7 },
    strengths: ["Réalisations chiffrées"],
    corrections: [{ priority: "high", target: "cv", text: "Mettre en avant le projet NLP." }],
  };
}

const SUMMARY: ApplicationSummary = {
  id: "app-1",
  organization: "Énergie Exemple",
  position: "Stage data scientist",
  status: "draft",
  lang: "fr",
  template: "modern",
  ats_score: 92,
  jury_score_before: 74,
  jury_score_after: 84,
  compaction_level: 0,
  sent_at: null,
  created_at: "2026-11-10T10:00:00Z",
  updated_at: "2026-11-10T10:00:00Z",
};

const DETAIL: ApplicationDetail = {
  ...SUMMARY,
  email_subject: "Candidature : Stage data scientist",
  email_body: "Madame, Monsieur,\nJe vous adresse ma candidature.",
  offer_text: OFFER,
  documents: null,
  files: { cv: "/api/applications/app-1/files/cv", letter: "/api/applications/app-1/files/letter" },
  report: {
    warnings: ["Compétences retirées car absentes de ton parcours : Kubernetes."],
    keywords: ["Python", "Spark"],
    removed_skills: ["Kubernetes"],
    tips: ["Contacte la responsable de l'équipe data."],
    gaps: [],
    ats_before: null,
    ats: {
      score: 92,
      checks_score: 100,
      coverage: 80,
      checks: [
        { key: "no_ligatures", ok: true, detail: "" },
        { key: "links_clickable", ok: false, detail: "Liens non cliquables : x." },
      ],
      keywords_found: ["Python"],
      keywords_missing: ["Spark"],
      pages: 1,
      text: "Camille Exemple",
      links: [],
    },
    jury_before: jury(74, "maybe"),
    jury_after: jury(84, "interview"),
    revision_applied: true,
    revision_kept: true,
    compaction_level: 0,
    pages: 1,
    target_pages: 1,
    letter_pages: 1,
    engine: "typst",
    cv_file: "CV_Camille-Exemple.pdf",
    letter_file: "Lettre_Camille-Exemple.pdf",
    edited: false,
  },
};

function setup() {
  const posted: { body?: Record<string, unknown> } = {};
  let listed: ApplicationSummary[] = [];
  mockApi({
    "GET /api/llm/status": () => DEMO_STATUS,
    "GET /api/settings": () => SETTINGS,
    "GET /api/applications": () => listed,
    "GET /api/applications/app-1": () => DETAIL,
    "POST /api/applications": (init) => {
      posted.body = JSON.parse(String(init?.body)) as Record<string, unknown>;
      listed = [SUMMARY];
      return makeJob({ id: "job-9", type: "application", status: "running" });
    },
  });
  return { posted };
}

describe("WorkshopPage", () => {
  beforeEach(() => {
    void i18n.changeLanguage("fr");
    FakeEventSource.install();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("refuses a too short offer, then starts a job with the settings defaults", async () => {
    const user = userEvent.setup();
    const { posted } = setup();
    renderApp("/workshop");

    const submit = await screen.findByRole("button", { name: "Préparer ma candidature" });
    await user.type(screen.getByLabelText("Texte de l'offre"), "Stage data");
    await user.click(submit);
    expect(await screen.findByRole("alert")).toHaveTextContent("au moins 80 caractères");
    expect(posted.body).toBeUndefined();

    await user.clear(screen.getByLabelText("Texte de l'offre"));
    await user.click(screen.getByLabelText("Texte de l'offre"));
    await user.paste(OFFER);
    await user.click(submit);

    await waitFor(() => expect(posted.body).toBeDefined());
    expect(posted.body).toMatchObject({
      offer_text: OFFER,
      lang: "fr",
      template: "classic",
      jury: true,
      revision: true,
      threshold: 82,
    });
    expect(FakeEventSource.last().url).toBe("/api/jobs/job-9/events");
  });

  it("follows the job live, then shows the scores before and after the revision", async () => {
    const user = userEvent.setup();
    setup();
    const { router } = renderApp("/workshop");

    await user.click(await screen.findByLabelText("Texte de l'offre"));
    await user.paste(OFFER);
    await user.click(screen.getByRole("button", { name: "Préparer ma candidature" }));

    const source = await waitFor(() => FakeEventSource.last());
    act(() =>
      source.emit(
        "progress",
        makeJob({
          id: "job-9",
          status: "running",
          progress: 45,
          steps: [
            { key: "draft", status: "done" },
            { key: "layout", status: "running" },
            { key: "ats_check", status: "pending" },
            { key: "jury", status: "pending" },
            { key: "revision", status: "pending" },
          ],
        }),
      ),
    );
    expect(await screen.findByTestId("job-status")).toHaveTextContent("En cours : Mise en page");

    act(() =>
      source.emit(
        "end",
        makeJob({ id: "job-9", status: "succeeded", progress: 100, result: { application_id: "app-1" } }),
      ),
    );
    expect(
      await screen.findByRole("heading", { name: "Stage data scientist" }),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe("?id=app-1");
    expect(screen.getByTestId("pdf-preview")).toHaveAttribute(
      "src",
      expect.stringContaining("/api/applications/app-1/files/cv?v="),
    );
    expect(screen.getByTestId("warnings")).toHaveTextContent("Kubernetes");

    await user.click(screen.getByRole("tab", { name: "Contrôle qualité" }));
    expect(screen.getByTestId("jury-score-before")).toHaveTextContent("74");
    expect(screen.getByTestId("jury-score-final")).toHaveTextContent("84");
    expect(screen.getByText("Entretien")).toBeInTheDocument();
    expect(within(screen.getByTestId("keywords-missing")).getByText("Spark")).toBeInTheDocument();
    expect(screen.getByText("Liens non cliquables : x.")).toBeInTheDocument();

    const recent = await screen.findByTestId("recent-applications");
    expect(recent).toHaveTextContent("Énergie Exemple");
  });
});
