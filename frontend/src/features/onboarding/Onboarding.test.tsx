import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "@/i18n";
import type { ProviderInfo, Settings, SettingsRead } from "@/lib/api";
import { DEMO_STATUS, mockApi, renderApp } from "@/test/utils";

const PROVIDERS: ProviderInfo[] = [
  { name: "mock", implemented: true, personal_use_only: false, default_model: null, suggested_models: [] },
  {
    name: "anthropic_api",
    implemented: true,
    personal_use_only: false,
    default_model: "claude-sonnet-5-5",
    suggested_models: ["claude-sonnet-5-5"],
  },
  {
    name: "claude_code_cli",
    implemented: true,
    personal_use_only: true,
    default_model: null,
    suggested_models: ["sonnet"],
  },
  {
    name: "openai_compatible",
    implemented: false,
    personal_use_only: false,
    default_model: null,
    suggested_models: [],
  },
];

const DOCUMENT_DEFAULTS = {
  engine: "typst",
  template: "modern",
  language: "fr",
  jury: true,
  revision: true,
  threshold: 82,
} as const;

function settings(overrides: Partial<SettingsRead> = {}): SettingsRead {
  return {
    ai: { provider: "mock", model: null, timeout_seconds: 300 },
    ui: { language: "fr", theme: "system" },
    documents: DOCUMENT_DEFAULTS,
    onboarding_completed: false,
    demo_mode: true,
    ...overrides,
  };
}

function setup(initial: SettingsRead) {
  const puts: Settings[] = [];
  let current = initial;
  const calls = mockApi({
    "GET /api/llm/status": () => DEMO_STATUS,
    "GET /api/llm/providers": () => PROVIDERS,
    "GET /api/settings": () => current,
    "PUT /api/settings": (init) => {
      const body = JSON.parse(String(init?.body)) as Settings;
      puts.push(body);
      current = { ...body, demo_mode: body.ai.provider === "mock" };
      return current;
    },
    "POST /api/llm/test": () => ({
      ok: true,
      provider: current.ai.provider,
      duration_ms: 1200,
      message: "Connexion réussie.",
      detail: "",
    }),
  });
  return { puts, calls };
}

describe("onboarding", () => {
  beforeEach(() => void i18n.changeLanguage("fr"));
  afterEach(() => vi.unstubAllGlobals());

  it("redirects to the wizard on first launch", async () => {
    setup(settings());
    const { router } = renderApp("/");
    expect(await screen.findByRole("heading", { name: "Bienvenue dans Postulo" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/welcome");
  });

  it("does not redirect once the wizard is completed", async () => {
    setup(settings({ onboarding_completed: true }));
    renderApp("/");
    expect(await screen.findByRole("heading", { level: 1, name: "Tableau de bord" })).toBeInTheDocument();
  });

  it("walks through the five steps and marks the onboarding as completed", async () => {
    const user = userEvent.setup();
    const { puts } = setup(settings());
    const { router } = renderApp("/welcome");

    expect(await screen.findByRole("heading", { name: "Choisis ton fournisseur d'IA" })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Tester la connexion" }));
    expect(await screen.findByTestId("connection-result")).toHaveTextContent("Connexion réussie.");

    await user.click(screen.getByRole("button", { name: /Suivant/ }));
    expect(screen.getByRole("heading", { name: "Ton parcours" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Remplir plus tard/ }));
    expect(screen.getByRole("heading", { name: "Ton objectif" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /4\. Sources/ }));
    expect(screen.getByText("Les sources arrivent bientôt")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Suivant/ }));
    await user.click(screen.getByRole("button", { name: /Terminer/ }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(puts.at(-1)?.onboarding_completed).toBe(true);
  });
});

describe("AI settings", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows the personal-use note for Claude Code and saves before testing", async () => {
    const user = userEvent.setup();
    const { puts } = setup(settings({ onboarding_completed: true }));
    renderApp("/settings");

    await user.click(await screen.findByLabelText(/Claude Code/));
    expect(screen.getByRole("note")).toHaveTextContent("usage personnel");
    expect(screen.getByText("Usage personnel")).toBeInTheDocument();
    expect(screen.getByLabelText(/Compatible OpenAI/)).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Tester la connexion" }));
    expect(await screen.findByTestId("connection-result")).toHaveTextContent("Connexion réussie.");
    expect(puts[0]?.ai.provider).toBe("claude_code_cli");
    expect(puts[0]?.onboarding_completed).toBe(true);
  });

  it("asks for the API key without ever displaying it", async () => {
    const user = userEvent.setup();
    let savedKey = "";
    setup(settings({ onboarding_completed: true }));
    const fetchMock = vi.mocked(fetch);
    const base = fetchMock.getMockImplementation();
    fetchMock.mockImplementation(async (input, init) => {
      if (String(input) === "/api/llm/api-key" && init?.method === "PUT") {
        savedKey = (JSON.parse(String(init.body)) as { api_key: string }).api_key;
        return new Response(null, { status: 204 });
      }
      return base!(input, init);
    });
    renderApp("/settings");

    await user.click(await screen.findByLabelText(/API Anthropic/));
    const key = screen.getByLabelText("Clé API Anthropic");
    expect(key).toHaveAttribute("type", "password");
    await user.type(key, "sk-ant-test-123456");
    await user.click(screen.getByRole("button", { name: "Enregistrer la clé" }));
    await waitFor(() => expect(savedKey).toBe("sk-ant-test-123456"));
    expect(key).toHaveValue("");
  });
});
