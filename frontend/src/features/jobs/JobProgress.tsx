import { CircleAlert, CircleCheck, CircleDashed, LoaderCircle } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { Progress } from "@/components/ui/progress";
import { FINAL_JOB_STATUSES, type Job, type StepStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

import { useJobEvents } from "./useJobEvents";

/** Steps of an application job (and of the demo job, which mimics it). */
const STEP_KEYS = ["draft", "layout", "ats_check", "jury", "revision"] as const;
type StepKey = (typeof STEP_KEYS)[number];

function isKnownStep(key: string): key is StepKey {
  return (STEP_KEYS as readonly string[]).includes(key);
}

const STEP_ICON: Record<StepStatus, typeof CircleCheck> = {
  pending: CircleDashed,
  running: LoaderCircle,
  done: CircleCheck,
  failed: CircleAlert,
};

interface JobProgressProps {
  initial: Job;
  /** Called once with the final job (succeeded, failed or interrupted). */
  onFinished: (job: Job) => void;
  /** Text shown when the job succeeded. */
  successText: (job: Job) => string;
}

/** Live progress of a background job (SSE), with an aria-live status line. */
export function JobProgress({ initial, onFinished, successText }: JobProgressProps) {
  const { t } = useTranslation();
  const { job, reconnecting } = useJobEvents(initial.id, initial);
  const current = job ?? initial;
  const finished = FINAL_JOB_STATUSES.includes(current.status);

  useEffect(() => {
    if (finished) onFinished(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, when the job ends
  }, [finished]);

  const runningStep = current.steps.find((step) => step.status === "running");
  const stepLabel = (key: string) => (isKnownStep(key) ? t(`demoJob.steps.${key}`) : key);

  const statusText =
    current.status === "running"
      ? t("demoJob.status.running", { step: runningStep ? stepLabel(runningStep.key) : "" })
      : current.status === "succeeded"
        ? successText(current)
        : t(`demoJob.status.${current.status}`);

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center gap-3">
        <Progress value={current.progress} aria-label={t("demoJob.progressLabel")} />
        <span className="tabular w-11 text-right text-sm font-medium text-ink">
          {current.progress}&nbsp;%
        </span>
      </div>
      <p
        aria-live="polite"
        data-testid="job-status"
        className={cn(
          "text-sm",
          current.status === "succeeded" && "text-success",
          (current.status === "failed" || current.status === "interrupted") && "text-danger",
          current.status === "running" && "text-muted",
        )}
      >
        {current.error && current.status === "failed" ? current.error : statusText}
      </p>
      {reconnecting ? (
        <p className="text-sm text-warning">{t("demoJob.connectionLost")}</p>
      ) : null}
      <ol className="grid grid-cols-5 gap-2" aria-label={t("demoJob.progressLabel")}>
        {current.steps.map((step) => {
          const Icon = STEP_ICON[step.status];
          return (
            <li
              key={step.key}
              data-status={step.status}
              className={cn(
                "flex flex-col gap-1.5 rounded-md border border-border bg-surface-raised p-2.5 text-sm",
                step.status === "running" && "border-primary/40 ring-1 ring-primary/20",
              )}
            >
              <Icon
                aria-hidden="true"
                className={cn(
                  "size-4",
                  step.status === "pending" && "text-muted",
                  step.status === "running" && "animate-spin text-primary",
                  step.status === "done" && "text-success",
                  step.status === "failed" && "text-danger",
                )}
              />
              <span className="font-medium text-ink">{stepLabel(step.key)}</span>
              <span className="text-xs text-muted">{t(`demoJob.stepStatus.${step.status}`)}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
