import { expect, test } from "@playwright/test";

import { completeOnboarding } from "./helpers";

test.beforeEach(async ({ request }) => {
  await completeOnboarding(request);
});

test("home shows a clean empty state in demo mode", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Postulo");
  await expect(page.getByRole("heading", { level: 1, name: "Tableau de bord" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ton espace est prêt" })).toBeVisible();
  await expect(page.getByText("Mode démo")).toBeVisible();
  await expect(page.getByTestId("ai-calls")).toHaveText("0 appel IA aujourd'hui");
});

test("the demo job shows live progress until it finishes", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Lancer la démonstration" }).click();

  const status = page.getByTestId("job-status");
  await expect(status).toContainText("En cours");

  // Progress is observed strictly between 0 and 100: updates arrive live.
  const bar = page.getByRole("progressbar").first();
  await expect
    .poll(async () => Number(await bar.getAttribute("aria-valuenow")), { timeout: 10_000 })
    .toBeGreaterThan(0);
  const midway = Number(await bar.getAttribute("aria-valuenow"));
  expect(midway).toBeLessThan(100);

  await expect(status).toHaveText("Terminé. Note simulée : 82/100.", { timeout: 20_000 });
  await expect(bar).toHaveAttribute("aria-valuenow", "100");
  await expect(page.locator('li[data-status="done"]')).toHaveCount(5);
  await expect(page.getByTestId("ai-calls")).toHaveText("1 appel IA aujourd'hui");
});

test("client-side routes work when loaded directly", async ({ page }) => {
  await page.goto("/tracking");
  await expect(page.getByRole("heading", { level: 1, name: "Suivi" })).toBeVisible();
  await page.getByRole("link", { name: "Retour au tableau de bord" }).click();
  await expect(page).toHaveURL(/\/$/);
});
