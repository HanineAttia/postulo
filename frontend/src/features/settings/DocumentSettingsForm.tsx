import { LoaderCircle, Save } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import type { DocumentSettings, SettingsRead } from "@/lib/api";

import { toSettings, useSaveSettings, useSettings } from "./useSettings";

/** Réglages > Documents (SPEC 12.3): engine, default template and language, jury, threshold. */
export function DocumentSettingsForm() {
  const settings = useSettings();
  if (!settings.data) return <Skeleton className="h-40 w-full" />;
  return <Form initial={settings.data} />;
}

function Form({ initial }: { initial: SettingsRead }) {
  const { t } = useTranslation();
  const save = useSaveSettings();
  const [value, setValue] = useState<DocumentSettings>(initial.documents);
  const set = (patch: Partial<DocumentSettings>) => setValue((v) => ({ ...v, ...patch }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate(
      { ...toSettings(initial), documents: value },
      { onSuccess: () => toast.success(t("settings.ai.saved")) },
    );
  };

  return (
    <form className="flex flex-col gap-4" onSubmit={submit}>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field id="doc-engine" label={t("settings.documents.engine")}>
          <NativeSelect
            id="doc-engine"
            value={value.engine}
            onChange={(e) => set({ engine: e.target.value as DocumentSettings["engine"] })}
          >
            <option value="typst">{t("settings.documents.engines.typst")}</option>
            <option value="html">{t("settings.documents.engines.html")}</option>
          </NativeSelect>
        </Field>
        <Field id="doc-default-template" label={t("workshop.form.template")}>
          <NativeSelect
            id="doc-default-template"
            value={value.template}
            onChange={(e) => set({ template: e.target.value as DocumentSettings["template"] })}
          >
            <option value="modern">{t("workshop.templates.modern")}</option>
            <option value="classic">{t("workshop.templates.classic")}</option>
          </NativeSelect>
        </Field>
        <Field id="doc-default-lang" label={t("workshop.form.language")}>
          <NativeSelect
            id="doc-default-lang"
            value={value.language}
            onChange={(e) => set({ language: e.target.value as DocumentSettings["language"] })}
          >
            <option value="fr">{t("workshop.languages.fr")}</option>
            <option value="en">{t("workshop.languages.en")}</option>
          </NativeSelect>
        </Field>
      </div>
      <p className="text-sm text-muted">{t("settings.documents.engineHint")}</p>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={value.jury}
            onChange={(e) => set({ jury: e.target.checked })}
          />
          {t("workshop.form.jury")}
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={value.revision}
            onChange={(e) => set({ revision: e.target.checked })}
          />
          {t("workshop.form.revision")}
        </label>
        <span className="flex items-center gap-2">
          <label htmlFor="doc-threshold">{t("workshop.form.threshold")}</label>
          <Input
            id="doc-threshold"
            type="number"
            min={0}
            max={100}
            className="h-8 w-20"
            value={value.threshold}
            onChange={(e) => set({ threshold: Number(e.target.value) })}
          />
        </span>
      </div>
      <Button type="submit" className="self-start" disabled={save.isPending}>
        {save.isPending ? (
          <LoaderCircle className="animate-spin" aria-hidden="true" />
        ) : (
          <Save aria-hidden="true" />
        )}
        {t("settings.ai.save")}
      </Button>
    </form>
  );
}
