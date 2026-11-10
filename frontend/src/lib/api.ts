/** Typed client for the local Postulo API (same origin; Vite proxies /api in dev). */
import type { CareerProfile } from "@/features/profile/schema";

export type JobStatus = "pending" | "running" | "succeeded" | "failed" | "interrupted";
export type StepStatus = "pending" | "running" | "done" | "failed";

export interface JobStep {
  key: string;
  status: StepStatus;
}

export interface Job {
  id: string;
  type: string;
  status: JobStatus;
  progress: number;
  steps: JobStep[];
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export type ProviderName = "mock" | "claude_code_cli" | "anthropic_api" | "openai_compatible";

export interface LLMStatus {
  provider: ProviderName;
  model: string | null;
  demo_mode: boolean;
  available: boolean;
  reason: string;
  calls_today: number;
  has_api_key: boolean;
}

export interface ProviderInfo {
  name: ProviderName;
  implemented: boolean;
  personal_use_only: boolean;
  default_model: string | null;
  suggested_models: string[];
}

export interface ConnectionTest {
  ok: boolean;
  provider: ProviderName;
  duration_ms: number;
  message: string;
  detail: string;
}

export interface AISettings {
  provider: ProviderName;
  model: string | null;
  timeout_seconds: number;
}

export interface Settings {
  ai: AISettings;
  ui: { language: "fr" | "en"; theme: "system" | "light" | "dark" };
  onboarding_completed: boolean;
}

export interface SettingsRead extends Settings {
  demo_mode: boolean;
}

export interface StoredProfile {
  version: number;
  updated_at: string | null;
  profile: CareerProfile;
}

export interface Advice {
  key: string;
  section: string;
  points: number;
  params: Record<string, number | string>;
}

export interface Completeness {
  score: number;
  advice: Advice[];
}

export interface SectionDiff {
  section: string;
  added: string[];
  updated: string[];
  unchanged: number;
  current_count: number;
  incoming_count: number;
}

export interface FieldDiff {
  path: string;
  current: string | null;
  incoming: string | null;
  action: "filled" | "kept" | "extended";
}

export interface ImportDiff {
  sections: SectionDiff[];
  fields: FieldDiff[];
}

export interface ImportPreview {
  base_version: number;
  incoming: CareerProfile;
  merge_diff: ImportDiff;
  replace_diff: ImportDiff;
  warnings: string[];
}

export type ImportMode = "merge" | "replace";

export const FINAL_JOB_STATUSES: readonly JobStatus[] = ["succeeded", "failed", "interrupted"];

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, message: string, detail = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const isForm = init?.body instanceof FormData;
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: "application/json",
        // The browser sets the multipart boundary itself for FormData bodies.
        ...(isForm ? {} : { "Content-Type": "application/json" }),
        ...init?.headers,
      },
    });
  } catch (cause) {
    throw new ApiError(0, "network", String(cause));
  }
  if (!response.ok) {
    let message = response.statusText;
    let detail = "";
    try {
      const body = (await response.json()) as {
        detail?: unknown;
        error?: { message?: string; detail?: string };
      };
      message = body.error?.message ?? (typeof body.detail === "string" ? body.detail : message);
      detail = body.error?.detail ?? JSON.stringify(body);
    } catch {
      // non-JSON error body: keep the status text
    }
    throw new ApiError(response.status, message, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function json(method: string, body?: unknown): RequestInit {
  return { method, body: body === undefined ? undefined : JSON.stringify(body) };
}

function upload(file: File): RequestInit {
  const form = new FormData();
  form.append("file", file);
  return { method: "POST", body: form };
}

export const api = {
  llmStatus: () => request<LLMStatus>("/api/llm/status"),
  startDemoJob: () => request<Job>("/api/jobs/demo", { method: "POST" }),
  getJob: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  jobEventsUrl: (id: string) => `/api/jobs/${encodeURIComponent(id)}/events`,

  getSettings: () => request<SettingsRead>("/api/settings"),
  saveSettings: (settings: Settings) => request<SettingsRead>("/api/settings", json("PUT", settings)),
  providers: () => request<ProviderInfo[]>("/api/llm/providers"),
  testConnection: () => request<ConnectionTest>("/api/llm/test", json("POST")),
  saveApiKey: (apiKey: string) => request<void>("/api/llm/api-key", json("PUT", { api_key: apiKey })),
  deleteApiKey: () => request<void>("/api/llm/api-key", json("DELETE")),

  getProfile: () => request<StoredProfile>("/api/profile"),
  saveProfile: (version: number, profile: CareerProfile) =>
    request<StoredProfile>("/api/profile", json("PUT", { version, profile })),
  completeness: () => request<Completeness>("/api/profile/completeness"),
  loadSample: (force = false) =>
    request<StoredProfile>("/api/profile/sample", json("POST", { force })),
  exportUrl: (format: "json" | "yaml") => `/api/profile/export?format=${format}`,
  importBackup: (file: File) => request<ImportPreview>("/api/profile/import-backup", upload(file)),
  importCv: (file: File) => request<Job>("/api/profile/import-cv", upload(file)),
  applyImport: (mode: ImportMode, incoming: CareerProfile, version: number) =>
    request<StoredProfile>("/api/profile/apply", json("POST", { mode, incoming, version })),
};
