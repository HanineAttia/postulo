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

export type DocLang = "fr" | "en";
export type TemplateName = "modern" | "classic";
export type EngineName = "typst" | "html";

export interface DocumentSettings {
  engine: EngineName;
  template: TemplateName;
  language: DocLang;
  jury: boolean;
  revision: boolean;
  threshold: number;
}

export interface Settings {
  ai: AISettings;
  ui: { language: "fr" | "en"; theme: "system" | "light" | "dark" };
  documents: DocumentSettings;
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

// --- application workshop (SPEC 7) ---------------------------------------------------------

export interface ContactLink {
  label: string;
  url: string;
  kind: "email" | "phone" | "linkedin" | "github" | "portfolio" | "other";
}

export interface DocEntry {
  ref: string;
  title: string;
  subtitle: string;
  location: string;
  dates: string;
  url: string | null;
  bullets: string[];
  details: string;
}

export interface DocLine {
  label: string;
  text: string;
}

export interface DocSection {
  key: string;
  title: string;
  entries: DocEntry[];
  lines: DocLine[];
}

export interface DocLayout {
  template: TemplateName;
  font: string;
  accent: string;
  ink: string;
  size: number;
  margin_x: number;
  margin_y: number;
  leading: number;
  gap: number;
  item_gap: number;
  level: number;
}

export interface CvDocument {
  lang: DocLang;
  name: string;
  title: string;
  summary: string;
  contact: { city: string; links: ContactLink[] };
  sections: DocSection[];
  layout: DocLayout;
}

export interface LetterDocument {
  lang: DocLang;
  name: string;
  contact: { city: string; links: ContactLink[] };
  place_date: string;
  recipient: string[];
  subject: string;
  salutation: string;
  paragraphs: string[];
  closing: string;
  layout: DocLayout;
}

export interface EditableDocuments {
  cv: CvDocument;
  letter: LetterDocument;
}

export interface AtsCheck {
  key: string;
  ok: boolean;
  detail: string;
}

export interface AtsReport {
  score: number;
  checks_score: number;
  coverage: number | null;
  checks: AtsCheck[];
  keywords_found: string[];
  keywords_missing: string[];
  pages: number;
  text: string;
  links: string[];
}

export const JURY_CRITERIA = [
  "fit",
  "impact",
  "clarity",
  "keywords",
  "credibility",
  "letter",
  "form",
] as const;
export type JuryCriterion = (typeof JURY_CRITERIA)[number];

export interface JuryReport {
  score: number;
  decision: "interview" | "maybe" | "reject";
  six_second_impression: string;
  criteria: Partial<Record<JuryCriterion, number>>;
  strengths: string[];
  corrections: { priority: "high" | "medium" | "low"; target: string; text: string }[];
}

export interface ApplicationReport {
  warnings: string[];
  keywords: string[];
  removed_skills: string[];
  tips: string[];
  gaps: string[];
  ats_before: AtsReport | null;
  ats: AtsReport | null;
  jury_before: JuryReport | null;
  jury_after: JuryReport | null;
  revision_applied: boolean;
  revision_kept: boolean;
  compaction_level: number;
  pages: number;
  target_pages: number;
  letter_pages: number;
  engine: EngineName;
  cv_file: string;
  letter_file: string;
  edited: boolean;
}

export type ApplicationStatus =
  | "draft"
  | "sent"
  | "followed_up"
  | "interview"
  | "rejected"
  | "offer_received"
  | "no_answer"
  | "withdrawn";

export interface ApplicationSummary {
  id: string;
  organization: string;
  position: string;
  status: ApplicationStatus;
  lang: DocLang;
  template: TemplateName;
  ats_score: number | null;
  jury_score_before: number | null;
  jury_score_after: number | null;
  compaction_level: number | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationDetail extends ApplicationSummary {
  email_subject: string;
  email_body: string;
  offer_text: string;
  report: ApplicationReport;
  documents: EditableDocuments | null;
  files: Partial<Record<"cv" | "letter", string>>;
}

export interface ApplicationCreate {
  offer_text: string;
  organization?: string;
  position?: string;
  lang?: DocLang;
  template?: TemplateName;
  engine?: EngineName;
  jury?: boolean;
  revision?: boolean;
  threshold?: number;
}

export interface DocumentsUpdate {
  documents: EditableDocuments;
  email_subject: string;
  email_body: string;
}

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

  sampleOffer: () => request<{ text: string }>("/api/applications/sample-offer"),
  createApplication: (body: ApplicationCreate) =>
    request<Job>("/api/applications", json("POST", body)),
  listApplications: () => request<ApplicationSummary[]>("/api/applications"),
  getApplication: (id: string) =>
    request<ApplicationDetail>(`/api/applications/${encodeURIComponent(id)}`),
  updateDocuments: (id: string, body: DocumentsUpdate) =>
    request<ApplicationDetail>(
      `/api/applications/${encodeURIComponent(id)}/documents`,
      json("PUT", body),
    ),
  markSent: (id: string) =>
    request<ApplicationDetail>(`/api/applications/${encodeURIComponent(id)}/sent`, json("POST")),
  openFolder: (id: string) =>
    request<void>(`/api/applications/${encodeURIComponent(id)}/open-folder`, json("POST")),
};
