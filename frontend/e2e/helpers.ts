import type { APIRequestContext } from "@playwright/test";

const DEMO_SETTINGS = {
  ai: { provider: "mock", model: null, timeout_seconds: 300 },
  ui: { language: "fr", theme: "system" },
};

export async function completeOnboarding(request: APIRequestContext, done = true) {
  await request.put("/api/settings", { data: { ...DEMO_SETTINGS, onboarding_completed: done } });
}

/** Start from an empty career library. */
export async function resetProfile(request: APIRequestContext) {
  const current = (await (await request.get("/api/profile")).json()) as { version: number };
  await request.post("/api/profile/apply", {
    data: { mode: "replace", incoming: {}, version: current.version },
  });
}
