import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, CircleDashed, LoaderCircle, Play, RotateCcw } from "lucide-react";
import { useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ApiError, api, FINAL_JOB_STATUSES, type Job, type StepStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

import { useJobEvents } from "./useJobEvents";

const DEMO_STEP_KEYS = ["draft", "layout", "ats_check", "jury", "revision"] as const;
type DemoStepKey = (typeof DEMO_STEP_KEYS)[number];

function isDemoStep(key: string): key is DemoStepKey {
  return (DEMO_STEP_KEYS as readonly string[]).includes(key);
}

const STEP_ICON: Record<StepStatus, typeof CircleCheck> = {
  pending: CircleDashed,
  running: LoaderCircle,
  done: CircleCheck,
  failed: CircleAlert,
};

export function DemoJobCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const start = useMutation({ mutationFn: api.startDemoJob });
  const job = start.data ?? null;
  const refreshAiCounter = useCallback(
    () => void queryClient.invalidateQueries({ queryKey: ["llm-status"] }),
    [queryClient],
  );

  return (
    <Card aria-labelledby="demo-job-title">
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <CardTitle id="demo-job-title">{t("demoJob.title")}</CardTitle>
          <CardDescription>{t("demoJob.description")}</CardDescription>
        </div>
        <Button
          variant={job ? "outline" : "default"}
          onClick={() => start.mutate()}
          disabled={start.isPending}
        >
          {start.isPending ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : job ? (
            <RotateCcw aria-hidden="true" />
          ) : (
            <Play aria-hidden="true" />
          )}
          {start.isPending ? t("demoJob.starting") : job ? t("demoJob.restart") : t("demoJob.start")}
        </Button>
      </CardHeader>
      <CardContent>
        {start.error ? (
          <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
            {start.error instanceof ApiError && start.error.status === 0
              ? t("errors.server")
              : start.error.message || t("errors.generic")}
          </p>
        ) : null}
        {job ? (
          <JobProgress
            key={job.id}
            initial={job}
            onFinished={refreshAiCounter}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function JobProgress({ initial, onFinished }: { initial: Job; onFinished: () => void }) {
  const { t } = useTranslation();
  const { job, reconnecting } = useJobEvents(initial.id, initial);
  const current = job ?? initial;
  const finished = FINAL_JOB_STATUSES.includes(current.status);

  useEffect(() => {
    if (finished) onFinished();
  }, [finished, onFinished]);

  const runningStep = current.steps.find((step) => step.status === "running");
  const stepLabel = (key: string) => (isDemoStep(key) ? t(`demoJob.steps.${key}`) : key);
  const score = typeof current.result?.score === "number" ? current.result.score : 0;

  const statusText =
    current.status === "running"
      ? t("demoJob.status.running", { step: runningStep ? stepLabel(runningStep.key) : "" })
      : current.status === "succeeded"
        ? t("demoJob.status.succeeded", { score })
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
