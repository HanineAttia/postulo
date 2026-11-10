import { useQueryClient } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JobProgress } from "@/features/jobs/JobProgress";
import type { Job } from "@/lib/api";
import { useDynamicT } from "@/lib/i18nKey";
import { cn } from "@/lib/utils";

import { ApplicationForm } from "./ApplicationForm";
import { ApplicationResult } from "./ApplicationResult";
import { APPLICATIONS_KEY, useApplications } from "./useApplications";

/** SPEC 12.3 "Atelier": options on the left, live progress then results on the right. */
export function WorkshopPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("id");
  const [job, setJob] = useState<Job | null>(null);
  const [running, setRunning] = useState(false);

  const select = (id: string | null) => setParams(id ? { id } : {});

  const onStarted = (started: Job) => {
    setJob(started);
    setRunning(true);
    select(null);
  };

  const onFinished = (finished: Job) => {
    setRunning(false);
    void queryClient.invalidateQueries({ queryKey: ["llm-status"] });
    void queryClient.invalidateQueries({ queryKey: APPLICATIONS_KEY });
    const id = finished.result?.application_id;
    if (finished.status === "succeeded" && typeof id === "string") {
      setJob(null);
      select(id);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("workshop.title")}</h1>
        <p className="text-sm text-muted">{t("workshop.subtitle")}</p>
      </div>
      <div className="grid items-start gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
        <div className="flex flex-col gap-6">
          <Card aria-labelledby="workshop-form-title">
            <CardHeader>
              <CardTitle id="workshop-form-title">{t("workshop.form.title")}</CardTitle>
              <CardDescription>{t("workshop.form.description")}</CardDescription>
            </CardHeader>
            <CardContent>
              <ApplicationForm onStarted={onStarted} busy={running} />
            </CardContent>
          </Card>
          <RecentApplications selectedId={selectedId} onSelect={select} />
        </div>
        <div className="flex min-w-0 flex-col gap-6">
          {job ? (
            <Card aria-labelledby="workshop-progress-title">
              <CardHeader>
                <CardTitle id="workshop-progress-title">{t("workshop.progress.title")}</CardTitle>
              </CardHeader>
              <CardContent>
                <JobProgress
                  key={job.id}
                  initial={job}
                  onFinished={onFinished}
                  successText={() => t("workshop.progress.done")}
                />
              </CardContent>
            </Card>
          ) : null}
          {selectedId ? (
            <ApplicationResult key={selectedId} id={selectedId} />
          ) : !job ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                <FileText className="size-8 text-muted" aria-hidden="true" />
                <h2 className="text-base font-semibold text-ink">{t("workshop.empty.title")}</h2>
                <p className="max-w-md text-sm text-muted">{t("workshop.empty.description")}</p>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function RecentApplications({
  selectedId,
  onSelect,
}: {
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const { t } = useTranslation();
  const dt = useDynamicT();
  const query = useApplications();
  const items = query.data ?? [];
  if (items.length === 0) return null;
  return (
    <Card aria-labelledby="recent-applications-title">
      <CardHeader>
        <CardTitle id="recent-applications-title">{t("workshop.recent.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-1" data-testid="recent-applications">
          {items.map((item) => {
            const jury = item.jury_score_after ?? item.jury_score_before;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  aria-current={item.id === selectedId ? "true" : undefined}
                  className={cn(
                    "flex w-full flex-col gap-1 rounded-md px-3 py-2 text-left text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring",
                    item.id === selectedId && "bg-primary-soft",
                  )}
                >
                  <span className="font-medium text-ink">
                    {item.position || t("workshop.result.untitled")}
                  </span>
                  <span className="flex flex-wrap items-center gap-2 text-xs text-muted">
                    {item.organization ? <span>{item.organization}</span> : null}
                    {item.ats_score !== null ? (
                      <span className="tabular">ATS {item.ats_score}</span>
                    ) : null}
                    {jury !== null ? (
                      <span className="tabular">{t("workshop.recent.jury", { score: jury })}</span>
                    ) : null}
                    <Badge variant={item.status === "draft" ? "neutral" : "success"}>
                      {dt(`workshop.status.${item.status}`)}
                    </Badge>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
