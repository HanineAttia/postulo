import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { JobStep, StepStatus } from "@/lib/api";
import { DEMO_STATUS, FakeEventSource, makeJob, mockApi, renderApp } from "@/test/utils";

const STEP_KEYS = ["draft", "layout", "ats_check", "jury", "revision"];

function steps(statuses: StepStatus[]): JobStep[] {
  return STEP_KEYS.map((key, index) => ({ key, status: statuses[index] ?? "pending" }));
}

describe("DemoJobCard", () => {
  let calls = 0;

  beforeEach(() => {
    calls = 0;
    FakeEventSource.install();
  });

  function setup() {
    const fetchMock = mockApi({
      "GET /api/llm/status": () => ({ ...DEMO_STATUS, calls_today: calls }),
      "POST /api/jobs/demo": () => makeJob(),
    });
    renderApp("/");
    return { user: userEvent.setup(), fetchMock };
  }

  it("follows a job live through SSE until it finishes", async () => {
    const { user, fetchMock } = setup();
    await user.click(screen.getByRole("button", { name: "Lancer la démonstration" }));

    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    const source = FakeEventSource.last();
    expect(source.url).toBe("/api/jobs/job-1/events");

    act(() =>
      source.emit(
        "progress",
        makeJob({ status: "running", progress: 40, steps: steps(["done", "running"]) }),
      ),
    );
    const bar = screen.getAllByRole("progressbar", { name: "Progression de la tâche" })[0];
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(screen.getByTestId("job-status")).toHaveTextContent("En cours : Mise en page");
    expect(screen.getByTestId("job-status")).toHaveAttribute("aria-live", "polite");

    calls = 1;
    act(() =>
      source.emit(
        "end",
        makeJob({
          status: "succeeded",
          progress: 100,
          steps: steps(["done", "done", "done", "done", "done"]),
          result: { score: 82 },
        }),
      ),
    );
    expect(screen.getByTestId("job-status")).toHaveTextContent("Terminé. Note simulée : 82/100.");
    expect(screen.getAllByText("Terminé")).toHaveLength(5);
    expect(source.readyState).toBe(FakeEventSource.CLOSED);
    expect(screen.getByRole("button", { name: "Relancer" })).toBeInTheDocument();

    // The header AI counter is refreshed once the job is done.
    await waitFor(() =>
      expect(screen.getByTestId("ai-calls")).toHaveTextContent("1 appel IA aujourd'hui"),
    );
    const statusCalls = fetchMock.mock.calls.filter(([url]) => url === "/api/llm/status");
    expect(statusCalls.length).toBeGreaterThanOrEqual(2);
  });

  it("shows the server error message when the job fails", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: "Lancer la démonstration" }));
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));
    act(() =>
      FakeEventSource.last().emit(
        "end",
        makeJob({ status: "failed", error: "Limite atteinte.", steps: steps(["failed"]) }),
      ),
    );
    expect(screen.getByTestId("job-status")).toHaveTextContent("Limite atteinte.");
    expect(screen.getByText("Échec")).toBeInTheDocument();
  });

  it("explains when the server cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    renderApp("/");
    await userEvent.setup().click(screen.getByRole("button", { name: "Lancer la démonstration" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur Postulo ne répond pas");
  });
});
