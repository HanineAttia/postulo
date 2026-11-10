import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import { completeOnboarding, resetProfile } from "./helpers";

const CV_FILE = fileURLToPath(new URL("./fixtures/cv-exemple.txt", import.meta.url));

test("onboarding, sample profile, reordering, CV import and export", async ({ page, request }) => {
  await resetProfile(request);
  await completeOnboarding(request, false);

  // First launch: the wizard comes first.
  await page.goto("/");
  await expect(page).toHaveURL(/\/welcome$/);
  await page.getByRole("button", { name: "Tester la connexion" }).click();
  await expect(page.getByTestId("connection-result")).toContainText("Connexion réussie.");
  await page.getByRole("button", { name: "Suivant" }).click();

  await page.getByRole("button", { name: /Profil d'exemple/ }).click();
  await expect(page.getByRole("heading", { name: "Ton objectif" })).toBeVisible();
  await expect(page.getByLabel("Domaine")).toHaveValue("Data science et intelligence artificielle");
  await page.getByRole("button", { name: "Enregistrer et continuer" }).click();
  await page.getByRole("button", { name: "Suivant" }).click();
  await page.getByRole("button", { name: "Terminer" }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByTestId("completeness-score")).toHaveText(/\d+/);

  // Reorder experiences and save.
  await page.goto("/profile?tab=experiences");
  const items = page.getByTestId("experiences-item");
  await expect(items.first()).toContainText("Stagiaire data scientist");
  await page.getByRole("button", { name: /^Descendre « Stagiaire data scientist/ }).click();
  await expect(items.first()).toContainText("Assistante de recherche");
  await page.getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByText("Parcours enregistré.")).toBeVisible();
  await page.reload();
  await expect(items.first()).toContainText("Assistante de recherche");

  // Edit a field with an invalid value: the save is refused and the field is flagged.
  await page.getByRole("tab", { name: "Identité et liens" }).click();
  await page.getByLabel("E-mail").fill("pas-un-email");
  await page.getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByText("Adresse e-mail invalide.")).toBeVisible();
  await page.getByRole("button", { name: "Annuler les modifications" }).click();

  // Import a CV (demo mode structures it without AI) and merge it without duplicates.
  await page.getByRole("tab", { name: "Import" }).click();
  await page.getByLabel(/Choisis ton CV/).setInputFiles(CV_FILE);
  const preview = page.getByTestId("import-preview");
  await expect(preview).toBeVisible({ timeout: 20_000 });
  await expect(preview).toContainText("Développeuse web · Agence Exemple");
  await preview.getByRole("button", { name: "Fusionner" }).click();
  await expect(page.getByText("Import fusionné dans ton parcours.")).toBeVisible();

  await page.getByRole("tab", { name: "Expériences" }).click();
  await expect(items).toHaveCount(3);

  // Importing the same CV again adds nothing.
  await page.getByRole("tab", { name: "Import" }).click();
  await page.getByLabel(/Choisis ton CV/).setInputFiles(CV_FILE);
  await expect(page.getByTestId("import-preview")).toContainText(
    "Rien de nouveau : tout est déjà dans ton parcours.",
    { timeout: 20_000 },
  );
  await page.getByRole("button", { name: "Annuler" }).click();

  // Export a backup.
  await page.getByRole("tab", { name: "Sauvegarde" }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Télécharger en JSON" }).click();
  expect((await download).suggestedFilename()).toMatch(/^postulo-parcours-.*\.json$/);
});
