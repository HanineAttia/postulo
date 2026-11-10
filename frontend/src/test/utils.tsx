import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { vi } from "vitest";

import { Providers } from "@/app/Providers";
import { routes } from "@/app/routes";
import type { Job, LLMStatus } from "@/lib/api";

export const DEMO_STATUS: LLMStatus = {
  provider: "mock",
  model: null,
  has_api_key: false,
  demo_mode: true,
  available: true,
  reason: "Mode démo",
  calls_today: 0,
};

export function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    type: "demo",
    status: "pending",
    progress: 0,
    steps: ["draft", "layout", "ats_check", "jury", "revision"].map((key) => ({
      key,
      status: "pending" as const,
    })),
    result: null,
    error: null,
    created_at: "2026-11-10T10:00:00Z",
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

type Handler = (init?: RequestInit) => unknown;

/** Stub `fetch` with a table of "METHOD /path" -> JSON body handlers. */
export function mockApi(handlers: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const key = `${init?.method ?? "GET"} ${url}`;
    const handler = handlers[key];
    if (!handler) return new Response(JSON.stringify({ detail: "Not found" }), { status: 404 });
    return new Response(JSON.stringify(handler(init)), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Minimal controllable EventSource. */
export class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: FakeEventSource[] = [];

  readonly url: string;
  readyState = FakeEventSource.OPEN;
  private listeners = new Map<string, Set<(event: MessageEvent<string>) => void>>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)?.add(listener);
  }

  removeEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.get(type)?.delete(listener);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }

  emit(type: string, data?: unknown) {
    const event = new MessageEvent(type, { data: data === undefined ? "" : JSON.stringify(data) });
    this.listeners.get(type)?.forEach((listener) => listener(event));
  }

  static install() {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  }

  static last(): FakeEventSource {
    const source = FakeEventSource.instances.at(-1);
    if (!source) throw new Error("No EventSource was created");
    return source;
  }
}

export function renderApp(path = "/") {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return { router, ...render(<Providers queryClient={queryClient}><RouterProvider router={router} /></Providers>) };
}
