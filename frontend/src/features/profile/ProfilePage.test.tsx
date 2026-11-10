import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import type { Completeness, ImportPreview, StoredProfile } from "@/lib/api";
import { DEMO_STATUS, mockApi, renderApp } from "@/test/utils";

import { type CareerProfile, emptyItem, emptyProfile } from "./schema";

function sampleProfile(): CareerProfile {
  const profile = emptyProfile();
  profile.identity.first_name = "Camille";
  profile.identity.last_name = "Exemple";
  profile.identity.email = "camille@example.com";
  profile.experiences = [
    { ...emptyItem("experiences"), id: "e1", title: "Stagiaire data", organization: "Alpha" },
    { ...emptyItem("experiences"), id: "e2", title: "Assistante", organization: "Beta" },
  ];
  return profile;
}

const COMPLETENESS: Completeness = {
  score: 62,
  advice: [{ key: "projects", section: "projects", points: 8, params: { count: 0 } }],
};

function setup(stored: StoredProfile) {
  const saved: { body?: { version: number; profile: CareerProfile } } = {};
  const fetchMock = mockApi({
    "GET /api/llm/status": () => DEMO_STATUS,
    "GET /api/profile": () => stored,
    "GET /api/profile/completeness": () => COMPLETENESS,
    "PUT /api/profile": (init) => {
      saved.body = JSON.parse(String(init?.body)) as typeof saved.body;
      return { ...stored, version: stored.version + 1, profile: saved.body?.profile };
    },
  });
  return { saved, fetchMock };
}

describe("ProfilePage", () => {
  beforeEach(() => void i18n.changeLanguage("fr"));
  afterEach(() => vi.unstubAllGlobals());

  it("shows the completeness score with advice linking to the right tab", async () => {
    setup({ version: 3, updated_at: null, profile: sampleProfile() });
    renderApp("/profile");
    expect(await screen.findByTestId("completeness-score")).toHaveTextContent("62");
    const advice = screen.getByRole("link", { name: /Ajoute au moins deux projets \(0/ });
    expect(advice).toHaveAttribute("href", "/profile?tab=projects");
  });

  it("reorders experiences with the move buttons and saves the new order", async () => {
    const user = userEvent.setup();
    const { saved } = setup({ version: 3, updated_at: null, profile: sampleProfile() });
    renderApp("/profile?tab=experiences");

    const items = await screen.findAllByTestId("experiences-item");
    expect(items[0]).toHaveTextContent("Stagiaire data · Alpha");
    await user.click(screen.getByRole("button", { name: "Descendre « Stagiaire data · Alpha »" }));

    const reordered = screen.getAllByTestId("experiences-item");
    expect(reordered[0]).toHaveTextContent("Assistante · Beta");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(saved.body).toBeDefined());
    expect(saved.body?.version).toBe(3);
    expect(saved.body?.profile.experiences.map((e) => e.id)).toEqual(["e2", "e1"]);
  });

  it("adds an experience with one achievement per line", async () => {
    const user = userEvent.setup();
    const { saved } = setup({ version: 1, updated_at: null, profile: sampleProfile() });
    renderApp("/profile?tab=experiences");

    await user.click(await screen.findByRole("button", { name: "Ajouter une expérience" }));
    const items = screen.getAllByTestId("experiences-item");
    const card = within(items[2] as HTMLElement);
    await user.type(card.getByLabelText("Intitulé du poste"), "Alternante");
    await user.type(card.getByLabelText("Début"), "2025-09");
    await user.type(card.getByLabelText("Réalisations"), "Fait A{Enter}{Enter}Fait B 30 %");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(saved.body).toBeDefined());
    const added = saved.body?.profile.experiences[2];
    expect(added?.title).toBe("Alternante");
    expect(added?.start).toBe("2025-09");
    expect(added?.end).toBeNull();
    expect(added?.achievements).toEqual(["Fait A", "Fait B 30 %"]);
  });

  it("blocks saving and flags the tab when a field is invalid", async () => {
    const user = userEvent.setup();
    const { saved } = setup({ version: 1, updated_at: null, profile: sampleProfile() });
    renderApp("/profile?tab=identity");

    const email = await screen.findByLabelText("E-mail");
    await user.clear(email);
    await user.type(email, "pas-un-email");
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(await screen.findByText("Adresse e-mail invalide.")).toBeInTheDocument();
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("1 section à corriger")).toBeInTheDocument();
    expect(saved.body).toBeUndefined();
  });

  it("opens on the import tab for a new user", async () => {
    setup({ version: 0, updated_at: null, profile: emptyProfile() });
    renderApp("/profile");
    expect(await screen.findByText("Choisis ton CV ou dépose-le ici")).toBeInTheDocument();
    expect(screen.queryByTestId("completeness-score")).not.toBeInTheDocument();
  });
});

describe("ImportPreviewPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("previews a merge, switches to replace and applies the chosen mode", async () => {
    const user = userEvent.setup();
    const preview: ImportPreview = {
      base_version: 2,
      incoming: sampleProfile(),
      merge_diff: {
        sections: [
          {
            section: "experiences",
            added: ["Assistante · Beta"],
            updated: ["Stagiaire data · Alpha"],
            unchanged: 0,
            current_count: 1,
            incoming_count: 2,
          },
        ],
        fields: [{ path: "identity.email", current: "a@b.fr", incoming: "c@d.fr", action: "kept" }],
      },
      replace_diff: {
        sections: [
          {
            section: "experiences",
            added: ["Stagiaire data · Alpha", "Assistante · Beta"],
            updated: [],
            unchanged: 0,
            current_count: 1,
            incoming_count: 2,
          },
        ],
        fields: [],
      },
      warnings: ["Champ ignoré (identity.phone) : invalide"],
    };
    let applied: { mode: string; version: number } | undefined;
    mockApi({
      "GET /api/llm/status": () => DEMO_STATUS,
      "GET /api/profile": () => ({ version: 2, updated_at: null, profile: sampleProfile() }),
      "GET /api/profile/completeness": () => COMPLETENESS,
      "POST /api/profile/import-backup": () => preview,
      "POST /api/profile/apply": (init) => {
        applied = JSON.parse(String(init?.body)) as typeof applied;
        return { version: 3, updated_at: null, profile: sampleProfile() };
      },
    });
    renderApp("/profile?tab=backup");

    const input = await screen.findByLabelText(/Choisis un fichier de sauvegarde/);
    await user.upload(input, new File(["{}"], "backup.json", { type: "application/json" }));

    const panel = await screen.findByTestId("import-preview");
    expect(within(panel).getByText("Champ ignoré (identity.phone) : invalide")).toBeInTheDocument();
    expect(within(panel).getByText("1 ajout")).toBeInTheDocument();
    expect(within(panel).getByText("1 complété")).toBeInTheDocument();
    expect(within(panel).getByText("E-mail")).toBeInTheDocument();

    await user.click(within(panel).getByLabelText(/Remplacer mon parcours/));
    expect(within(panel).getByText("1 remplacé")).toBeInTheDocument();
    await user.click(within(panel).getByRole("button", { name: "Remplacer" }));

    await waitFor(() => expect(applied).toEqual(expect.objectContaining({ mode: "replace", version: 2 })));
    await waitFor(() => expect(screen.queryByTestId("import-preview")).not.toBeInTheDocument());
  });
});
