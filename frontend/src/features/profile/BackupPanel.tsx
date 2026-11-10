import { useMutation } from "@tanstack/react-query";
import { Download, LoaderCircle, Sparkles } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type StoredProfile } from "@/lib/api";

import { FileDrop } from "./ImportCvPanel";
import { ImportPreviewPanel } from "./ImportPreviewPanel";
import { useLoadSample } from "./useProfile";

interface BackupPanelProps {
  hasContent: boolean;
  blocked: boolean;
  onApplied: (stored: StoredProfile) => void;
}

export function BackupPanel({ hasContent, blocked, onApplied }: BackupPanelProps) {
  const { t } = useTranslation();
  const restore = useMutation({ mutationFn: api.importBackup });
  const sample = useLoadSample();
  const [confirmSample, setConfirmSample] = useState(false);

  const loadSample = () => {
    if (hasContent && !confirmSample) {
      setConfirmSample(true);
      return;
    }
    sample.mutate(hasContent, {
      onSuccess: (stored) => {
        setConfirmSample(false);
        toast.success(t("backup.sampleLoaded"));
        onApplied(stored);
      },
      onError: (error) => toast.error(error.message || t("errors.generic")),
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <Card aria-labelledby="export-title">
        <CardHeader>
          <CardTitle id="export-title">{t("backup.exportTitle")}</CardTitle>
          <CardDescription>{t("backup.exportDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {(["json", "yaml"] as const).map((format) => (
            <Button key={format} variant="outline" asChild>
              <a href={api.exportUrl(format)} download>
                <Download aria-hidden="true" />
                {t("backup.export", { format: format.toUpperCase() })}
              </a>
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card aria-labelledby="restore-title">
        <CardHeader>
          <CardTitle id="restore-title">{t("backup.restoreTitle")}</CardTitle>
          <CardDescription>{t("backup.restoreDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {restore.data ? (
            <ImportPreviewPanel
              preview={restore.data}
              blocked={blocked}
              onApplied={(stored) => {
                restore.reset();
                onApplied(stored);
              }}
              onCancel={() => restore.reset()}
            />
          ) : (
            <FileDrop
              accept=".json,.yaml,.yml"
              label={t("backup.chooseFile")}
              hint={t("backup.formats")}
              disabled={restore.isPending}
              onFile={(file) => restore.mutate(file)}
            />
          )}
          {restore.error ? (
            <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
              {restore.error.message || t("errors.generic")}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card aria-labelledby="sample-title">
        <CardHeader>
          <CardTitle id="sample-title">{t("backup.sampleTitle")}</CardTitle>
          <CardDescription>{t("backup.sampleDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Button
            variant={confirmSample ? "default" : "outline"}
            onClick={loadSample}
            disabled={sample.isPending || blocked}
          >
            {sample.isPending ? (
              <LoaderCircle className="animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles aria-hidden="true" />
            )}
            {confirmSample ? t("backup.sampleConfirm") : t("backup.sampleLoad")}
          </Button>
          {confirmSample ? (
            <>
              <span role="alert" className="text-sm text-warning">
                {t("backup.sampleWarning")}
              </span>
              <Button variant="ghost" onClick={() => setConfirmSample(false)}>
                {t("import.cancel")}
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
