/** Typed client for the local Postulo API (same origin; Vite proxies /api in dev). */

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
  demo_mode: boolean;
  available: boolean;
  reason: string;
  calls_today: number;
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
  try {
    response = await fetch(path, {
      ...init,
      headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers },
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
  return (await response.json()) as T;
}

export const api = {
  llmStatus: () => request<LLMStatus>("/api/llm/status"),
  startDemoJob: () => request<Job>("/api/jobs/demo", { method: "POST" }),
  getJob: (id: string) => request<Job>(`/api/jobs/${encodeURIComponent(id)}`),
  jobEventsUrl: (id: string) => `/api/jobs/${encodeURIComponent(id)}/events`,
};
