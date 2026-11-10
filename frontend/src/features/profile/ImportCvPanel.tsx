import { useMutation } from "@tanstack/react-query";
import { CircleCheck, CircleDashed, FileUp, LoaderCircle, CircleAlert } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useJobEvents } from "@/features/jobs/useJobEvents";
import { api, type ImportPreview, type Job, type StepStatus, type StoredProfile } from "@/lib/api";
import { cn } from "@/lib/utils";

import { ImportPreviewPanel } from "./ImportPreviewPanel";

const STEP_ICON: Record<StepStatus, typeof CircleCheck> = {
  pending: CircleDashed,
  running: LoaderCircle,
  done: CircleCheck,
  failed: CircleAlert,
};
const CV_STEPS = ["extract", "structure", "compare"] as const;

interface FileDropProps {
  accept: string;
  label: string;
  hint: string;
  disabled?: boolean;
  onFile: (file: File) => void;
}

/** A keyboard-accessible file picker that also accepts drag and drop. */
export function FileDrop({ accept, label, hint, disabled, onFile }: FileDropProps) {
  const id = useId();
  const [over, setOver] = useState(false);
  return (
    <label
      htmlFor={id}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        const file = event.dataTransfer.files[0];
        if (file && !disabled) onFile(file);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-8 text-center transition-colors has-focus-visible:outline-2 has-focus-visible:outline-ring",
        over ? "border-primary bg-primary-soft" : "border-border bg-surface hover:bg-primary-soft/40",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      <FileUp className="size-6 text-primary" aria-hidden="true" />
      <span className="text-sm font-medium text-ink">{label}</span>
      <span className="text-xs text-muted">{hint}</span>
      <input
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </label>
  );
}

interface ImportCvPanelProps {
  blocked: boolean;
  onApplied: (stored: StoredProfile) => void;
}

export function ImportCvPanel({ blocked, onApplied }: ImportCvPanelProps) {
  const { t } = useTranslation();
  const start = useMutation({ mutationFn: api.importCv });
  const [dismissed, setDismissed] = useState<string | null>(null);
  const started = start.data && start.data.id !== dismissed ? start.data : null;

  return (
    <Card aria-labelledby="import-cv-title">
      <CardHeader>
        <CardTitle id="import-cv-title">{t("import.cvTitle")}</CardTitle>
        <CardDescription>{t("import.cvDescription")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {!started ? (
          <FileDrop
            accept=".pdf,.docx,.txt,.md"
            label={t("import.chooseCv")}
            hint={t("import.cvFormats")}
            disabled={start.isPending}
            onFile={(file) => start.mutate(file)}
          />
        ) : null}
        {start.isPending ? (
          <p className="flex items-center gap-2 text-sm text-muted" role="status">
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
            {t("import.uploading")}
          </p>
        ) : null}
        {start.error ? (
          <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
            {start.error.message || t("errors.generic")}
          </p>
        ) : null}
        {started ? (
          <CvImportJob
            key={started.id}
            initial={started}
            blocked={blocked}
            onApplied={(stored) => {
              setDismissed(started.id);
              onApplied(stored);
            }}
            onCancel={() => setDismissed(started.id)}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function CvImportJob({
  initial,
  blocked,
  onApplied,
  onCancel,
}: {
  initial: Job;
  blocked: boolean;
  onApplied: (stored: StoredProfile) => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const { job } = useJobEvents(initial.id, initial);
  const current = job ?? initial;

  if (current.status === "succeeded" && current.result) {
    return (
      <ImportPreviewPanel
        preview={current.result as unknown as ImportPreview}
        blocked={blocked}
        onApplied={onApplied}
        onCancel={onCancel}
      />
    );
  }
  const failed = current.status === "failed" || current.status === "interrupted";
  return (
    <div className="flex flex-col gap-3">
      <Progress value={current.progress} aria-label={t("import.progressLabel")} />
      <ol className="flex flex-col gap-1.5" aria-live="polite">
        {current.steps.map((step) => {
          const Icon = STEP_ICON[step.status];
          const known = (CV_STEPS as readonly string[]).includes(step.key);
          return (
            <li key={step.key} className="flex items-center gap-2 text-sm">
              <Icon
                className={cn(
                  "size-4",
                  step.status === "running" && "animate-spin text-primary",
                  step.status === "done" && "text-success",
                  step.status === "failed" && "text-danger",
                  step.status === "pending" && "text-muted",
                )}
                aria-hidden="true"
              />
              <span className={step.status === "pending" ? "text-muted" : "text-ink"}>
                {known ? t(`import.steps.${step.key as (typeof CV_STEPS)[number]}`) : step.key}
              </span>
            </li>
          );
        })}
      </ol>
      {failed ? (
        <div role="alert" className="flex flex-col gap-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
          <span>{current.error ?? t("errors.generic")}</span>
          <button type="button" onClick={onCancel} className="self-start font-medium underline">
            {t("import.retry")}
          </button>
        </div>
      ) : null}
    </div>
  );
}
