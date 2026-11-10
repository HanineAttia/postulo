import { expect, test } from "@playwright/test";

import { completeOnboarding } from "./helpers";

/**
 * Phase 2 journey (SPEC 14): sample profile + offer, live progress, one-page CV,
 * jury before and after, edit and regenerate without AI, "I sent it".
 */
test("prepare an application in demo mode, edit it and mark it as sent", async ({
  page,
  request,
}) => {
  test.setTimeout(90_000);
  await completeOnboarding(request);
  await request.post("/api/profile/sample", { data: { force: true } });

  await page.goto("/workshop");
  await expect(page.getByRole("heading", { level: 1, name: "Atelier" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Aucune candidature ouverte" })).toBeVisible();

  await page.getByRole("button", { name: "Utiliser l'offre d'exemple" }).click();
  await expect(page.getByLabel("Texte de l'offre")).toHaveValue(/Énergie Exemple/);
  await page.getByRole("button", { name: "Préparer ma candidature" }).click();

  // Live progress, then the result opens by itself.
  await expect(page.getByTestId("job-status")).toContainText("En cours");
  const title = page.getByRole("heading", { name: /Data scientist/ });
  await expect(title).toBeVisible({ timeout: 60_000 });
  await expect(page).toHaveURL(/\/workshop\?id=[0-9a-f]+$/);

  // One-page CV preview, served inline as a PDF.
  const preview = page.getByTestId("pdf-preview");
  await expect(preview).toHaveAttribute("src", /\/files\/cv\?v=/);
  await expect(page.getByTestId("document-facts")).toContainText("1 page(s)");
  const src = (await preview.getAttribute("src")) ?? "";
  const pdf = await request.get(src);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");

  // Quality: jury before and after the revision, ATS score >= 85.
  await page.getByRole("tab", { name: "Contrôle qualité" }).click();
  await expect(page.getByTestId("jury-score-before")).toHaveText("74");
  await expect(page.getByTestId("jury-score-final")).toHaveText("84");
  const ats = Number(await page.getByTestId("ats-score-final").textContent());
  expect(ats).toBeGreaterThanOrEqual(85);
  await expect(page.getByText("Aucune ligature")).toBeVisible();

  // The e-mail has no placeholder left.
  await page.getByRole("tab", { name: "E-mail" }).click();
  await expect(page.getByLabel("Message")).toHaveValue(/Camille Exemple/);
  await expect(page.getByLabel("Message")).not.toHaveValue(/\[/);

  // Edit and regenerate without any AI call.
  const counter = page.getByTestId("ai-calls");
  const callsBefore = await counter.textContent();
  await page.getByRole("tab", { name: "Éditer" }).click();
  await page.getByLabel("Accroche").fill("Accroche réécrite à la main pour cette offre.");
  await page.getByRole("button", { name: "Régénérer le PDF" }).click();
  await expect(page.getByText("PDF régénérés.")).toBeVisible();
  await expect(page.getByRole("tab", { name: "Documents" })).toHaveAttribute(
    "data-state",
    "active",
  );
  await page.getByRole("tab", { name: "Contrôle qualité" }).click();
  await page.getByText("Texte vu par l'ATS").click();
  await expect(page.getByText(/Accroche réécrite à la main/)).toBeVisible();
  await page.reload();
  await expect(counter).toHaveText(callsBefore ?? "");

  // The user sends the application (never the app), then marks it.
  await page.getByRole("button", { name: "J'ai envoyé" }).click();
  await expect(page.getByText(/Envoyée le/)).toBeVisible();
  await expect(page.getByTestId("recent-applications")).toContainText("Envoyée");
});
