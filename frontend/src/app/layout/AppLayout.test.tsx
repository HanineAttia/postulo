import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "i18next";
import { act } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import { DEMO_STATUS, FakeEventSource, mockApi, renderApp } from "@/test/utils";

describe("AppLayout", () => {
  beforeEach(() => {
    FakeEventSource.install();
    mockApi({ "GET /api/llm/status": () => DEMO_STATUS });
  });

  it("shows the sidebar groups and every page of SPEC 12.2", () => {
    renderApp("/");
    const nav = screen.getByRole("navigation", { name: "Navigation principale" });
    for (const group of ["Trouver", "Candidater", "Se préparer", "Mon espace"]) {
      expect(within(nav).getByRole("heading", { name: group })).toBeInTheDocument();
    }
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Tableau de bord",
      "Offres",
      "Marché caché",
      "Organisations",
      "Atelier",
      "Suivi",
      "LinkedIn et réseau",
      "Coach d'entretien",
      "Mon parcours",
      "Réglages",
    ]);
    expect(within(nav).getByRole("link", { name: "Tableau de bord" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows a clean empty dashboard with demo mode and the AI counter", async () => {
    renderApp("/");
    expect(screen.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ton espace est prêt" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compléter mon parcours" })).toHaveAttribute(
      "href",
      "/profile",
    );
    expect(await screen.findByText("Mode démo")).toBeInTheDocument();
    expect(screen.getByTestId("ai-calls")).toHaveTextContent("0 appel IA aujourd'hui");
  });

  it("navigates to a page with a useful empty state", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await user.click(screen.getByRole("link", { name: "Offres" }));
    expect(screen.getByRole("heading", { level: 1, name: "Offres" })).toBeInTheDocument();
    expect(screen.getByText("Disponible en phase 3")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Offres" })).toHaveAttribute("aria-current", "page");
  });

  it("collapses the sidebar while keeping accessible link names", async () => {
    const user = userEvent.setup();
    renderApp("/");
    const toggle = screen.getByRole("button", { name: "Replier la barre latérale" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(toggle);

    const expand = screen.getByRole("button", { name: "Déplier la barre latérale" });
    expect(expand).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("heading", { name: "Trouver" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Réglages" })).toBeInTheDocument();
    expect(window.localStorage.getItem("postulo.sidebar")).toBe("collapsed");
    // Regression: links wrapped in a tooltip must keep real classes, not a stringified function.
    const active = screen.getByRole("link", { name: "Tableau de bord" });
    expect(active.className).toContain("text-primary");
    expect(active.className).not.toContain("=>");
  });

  it("switches the interface to English", async () => {
    renderApp("/");
    await act(() => i18n.changeLanguage("en"));
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Job offers" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });

  it("shows a not-found page for unknown routes", () => {
    renderApp("/does-not-exist");
    expect(screen.getByRole("heading", { level: 1, name: "Page introuvable" })).toBeInTheDocument();
  });
});
