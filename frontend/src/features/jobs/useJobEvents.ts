import { useEffect, useState } from "react";

import { api, FINAL_JOB_STATUSES, type Job } from "@/lib/api";

interface JobEventsState {
  job: Job | null;
  /** True while the browser is reconnecting after a dropped connection. */
  reconnecting: boolean;
}

/**
 * Follow a background job live through Server-Sent Events.
 * The server replays the current state on (re)connection, so a dropped
 * connection only needs EventSource's built-in retry.
 */
export function useJobEvents(jobId: string | null, initial: Job | null = null): JobEventsState {
  const [state, setState] = useState<JobEventsState>({ job: initial, reconnecting: false });

  useEffect(() => {
    if (!jobId) return;
    const source = new EventSource(api.jobEventsUrl(jobId));

    const onUpdate = (event: MessageEvent<string>) => {
      const job = JSON.parse(event.data) as Job;
      setState({ job, reconnecting: false });
      if (FINAL_JOB_STATUSES.includes(job.status)) source.close();
    };
    const onError = () => {
      if (source.readyState !== EventSource.CLOSED) {
        setState((previous) => ({ ...previous, reconnecting: true }));
      }
    };

    source.addEventListener("progress", onUpdate);
    source.addEventListener("end", onUpdate);
    source.addEventListener("error", onError);
    return () => {
      source.removeEventListener("progress", onUpdate);
      source.removeEventListener("end", onUpdate);
      source.removeEventListener("error", onError);
      source.close();
    };
  }, [jobId]);

  return state;
}
