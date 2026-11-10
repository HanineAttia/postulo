import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Play, RotateCcw } from "lucide-react";
import { useCallback } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, api } from "@/lib/api";

import { JobProgress } from "./JobProgress";

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
            successText={(done) =>
              t("demoJob.status.succeeded", {
                score: typeof done.result?.score === "number" ? done.result.score : 0,
              })
            }
          />
        ) : null}
      </CardContent>
    </Card>
  );
}
