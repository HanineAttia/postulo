import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests run against the real backend in demo mode, serving the
 * compiled frontend (run `pnpm build` first). User data goes to a throwaway
 * POSTULO_HOME, so tests never touch real data.
 */
const PORT = 8790;
const postuloHome = process.env.POSTULO_E2E_HOME ?? mkdtempSync(join(tmpdir(), "postulo-e2e-"));

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  // One backend and one data directory are shared: run test files one after another.
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    locale: "fr-FR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 800 },
        // Optional: PLAYWRIGHT_CHANNEL=msedge uses the installed (signed) Microsoft Edge.
        channel: process.env.PLAYWRIGHT_CHANNEL,
      },
    },
  ],
  webServer: {
    command: `uv run postulo --no-browser --port ${PORT}`,
    cwd: "..",
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: { POSTULO_HOME: postuloHome, PYTHONUTF8: "1" },
  },
});
