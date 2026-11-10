import { CircleAlert, GitMerge, LoaderCircle, Replace, TriangleAlert } from "lucide-react";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ImportDiff, ImportMode, ImportPreview, StoredProfile } from "@/lib/api";
import { useDynamicT } from "@/lib/i18nKey";
import { cn } from "@/lib/utils";

import { useApplyImport } from "./useProfile";

interface ImportPreviewPanelProps {
  preview: ImportPreview;
  /** Unsaved form changes would be lost: applying is blocked until they are saved. */
  blocked?: boolean;
  onApplied: (stored: StoredProfile) => void;
  onCancel: () => void;
}

/** Shows what an import adds, updates or keeps, then merges or replaces on demand. */
export function ImportPreviewPanel({ preview, blocked, onApplied, onCancel }: ImportPreviewPanelProps) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<ImportMode>("merge");
  const apply = useApplyImport();
  const diff = mode === "merge" ? preview.merge_diff : preview.replace_diff;
  const groupId = useId();

  const submit = () =>
    apply.mutate(
      { mode, incoming: preview.incoming, version: preview.base_version },
      {
        onSuccess: (stored) => {
          toast.success(t(mode === "merge" ? "import.mergedToast" : "import.replacedToast"));
          onApplied(stored);
        },
        onError: (error) => toast.error(error.message || t("errors.generic")),
      },
    );

  return (
    <div className="flex flex-col gap-5" data-testid="import-preview">
      {preview.warnings.length > 0 ? (
        <div className="rounded-lg bg-warning-soft px-4 py-3 text-sm text-warning">
          <p className="flex items-center gap-2 font-medium">
            <TriangleAlert className="size-4" aria-hidden="true" />
            {t("import.warningsTitle")}
          </p>
          <ul className="mt-1 list-disc pl-6">
            {preview.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium text-ink">{t("import.modeLabel")}</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {(["merge", "replace"] as const).map((value) => {
            const Icon = value === "merge" ? GitMerge : Replace;
            const id = `${groupId}-${value}`;
            return (
              <label
                key={value}
                htmlFor={id}
                className={cn(
                  "flex cursor-pointer gap-3 rounded-lg border p-3 text-sm has-focus-visible:outline-2 has-focus-visible:outline-ring",
                  mode === value ? "border-primary bg-primary-soft" : "border-border",
                )}
              >
                <input
                  id={id}
                  type="radio"
                  name={groupId}
                  value={value}
                  checked={mode === value}
                  onChange={() => setMode(value)}
                  className="sr-only"
                />
                <Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                <span className="flex flex-col gap-0.5">
                  <span className="font-medium text-ink">{t(`import.mode.${value}`)}</span>
                  <span className="text-muted">{t(`import.modeHint.${value}`)}</span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <DiffSummary diff={diff} mode={mode} />

      {blocked ? (
        <p role="alert" className="flex items-center gap-2 text-sm text-warning">
          <CircleAlert className="size-4" aria-hidden="true" />
          {t("import.unsavedChanges")}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button onClick={submit} disabled={apply.isPending || blocked}>
          {apply.isPending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}
          {t(mode === "merge" ? "import.applyMerge" : "import.applyReplace")}
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          {t("import.cancel")}
        </Button>
      </div>
    </div>
  );
}

function DiffSummary({ diff, mode }: { diff: ImportDiff; mode: ImportMode }) {
  const { t } = useTranslation();
  const td = useDynamicT();
  const sections = diff.sections.filter(
    (s) => s.added.length || s.updated.length || s.unchanged || (mode === "replace" && s.current_count),
  );
  const filled = diff.fields.filter((f) => f.action !== "kept");
  const kept = diff.fields.filter((f) => f.action === "kept");
  const nothing = sections.every((s) => !s.added.length && !s.updated.length) && !filled.length;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-ink">{t("import.previewTitle")}</h3>
      {nothing && mode === "merge" ? (
        <p className="text-sm text-muted">{t("import.nothingNew")}</p>
      ) : null}
      <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
        {sections.map((section) => (
          <li key={section.section} className="flex flex-col gap-1.5 px-4 py-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-ink">
                {td(`profile.sections.${section.section}.title`)}
              </span>
              {section.added.length ? (
                <Badge variant="success">{t("import.added", { count: section.added.length })}</Badge>
              ) : null}
              {section.updated.length ? (
                <Badge variant="primary">
                  {t("import.updated", { count: section.updated.length })}
                </Badge>
              ) : null}
              {section.unchanged ? (
                <Badge>{t("import.unchanged", { count: section.unchanged })}</Badge>
              ) : null}
              {mode === "replace" && section.current_count ? (
                <Badge variant="danger">
                  {t("import.removed", { count: section.current_count })}
                </Badge>
              ) : null}
            </div>
            {[...section.added, ...section.updated].length ? (
              <p className="text-muted">{[...section.added, ...section.updated].join(" ; ")}</p>
            ) : null}
          </li>
        ))}
        {filled.length ? (
          <li className="px-4 py-3 text-sm">
            <span className="font-medium text-ink">{t("import.filledFields")}</span>
            <p className="text-muted">
              {filled.map((f) => `${td(pathLabel(f.path))} : ${f.incoming ?? ""}`).join(" ; ")}
            </p>
          </li>
        ) : null}
        {kept.length ? (
          <li className="px-4 py-3 text-sm">
            <span className="font-medium text-ink">{t("import.keptFields")}</span>
            <p className="text-muted">
              {kept.map((f) => td(pathLabel(f.path))).join(", ")}
            </p>
          </li>
        ) : null}
      </ul>
    </div>
  );
}

/** "identity.email" -> label key of the matching form field. */
function pathLabel(path: string): string {
  return path.includes(".") ? `profile.fields.${path}` : `profile.fields.main.${path}`;
}
