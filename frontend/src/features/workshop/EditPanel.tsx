import { LoaderCircle, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import type { ApplicationDetail, EditableDocuments, TemplateName } from "@/lib/api";

import { useUpdateDocuments } from "./useApplications";

const lines = (text: string) =>
  text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

/**
 * Edit the title, summary, bullets and letter, then regenerate the PDFs.
 * No AI call: the server only re-renders and re-runs the ATS check.
 */
export function EditPanel({
  detail,
  documents,
  onDone,
}: {
  detail: ApplicationDetail;
  documents: EditableDocuments;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<EditableDocuments>(() => structuredClone(documents));
  const update = useUpdateDocuments(detail.id);

  const setCv = (patch: Partial<EditableDocuments["cv"]>) =>
    setDraft((d) => ({ ...d, cv: { ...d.cv, ...patch } }));
  const setLetter = (patch: Partial<EditableDocuments["letter"]>) =>
    setDraft((d) => ({ ...d, letter: { ...d.letter, ...patch } }));
  const setBullets = (sectionIndex: number, entryIndex: number, text: string) =>
    setDraft((d) => {
      const sections = structuredClone(d.cv.sections);
      const entry = sections[sectionIndex]?.entries[entryIndex];
      if (entry) entry.bullets = text.split("\n");
      return { ...d, cv: { ...d.cv, sections } };
    });

  const save = () => {
    const cleaned = structuredClone(draft);
    for (const section of cleaned.cv.sections) {
      for (const entry of section.entries) entry.bullets = lines(entry.bullets.join("\n"));
    }
    cleaned.letter.paragraphs = cleaned.letter.paragraphs.map((p) => p.trim()).filter(Boolean);
    update.mutate(
      { documents: cleaned, email_subject: detail.email_subject, email_body: detail.email_body },
      {
        onSuccess: () => {
          toast.success(t("workshop.edit.saved"));
          onDone();
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted">{t("workshop.edit.intro")}</p>
      <div className="grid gap-3 sm:grid-cols-[1fr_200px]">
        <Field id="edit-title" label={t("workshop.edit.cvTitle")}>
          <Input
            id="edit-title"
            value={draft.cv.title}
            onChange={(event) => setCv({ title: event.target.value })}
          />
        </Field>
        <Field id="edit-template" label={t("workshop.form.template")}>
          <NativeSelect
            id="edit-template"
            value={draft.cv.layout.template}
            onChange={(event) =>
              setCv({
                layout: { ...draft.cv.layout, template: event.target.value as TemplateName },
              })
            }
          >
            <option value="modern">{t("workshop.templates.modern")}</option>
            <option value="classic">{t("workshop.templates.classic")}</option>
          </NativeSelect>
        </Field>
      </div>
      <Field id="edit-summary" label={t("workshop.edit.summary")}>
        <Textarea
          id="edit-summary"
          rows={3}
          value={draft.cv.summary}
          onChange={(event) => setCv({ summary: event.target.value })}
        />
      </Field>

      {draft.cv.sections.map((section, sectionIndex) =>
        section.entries.some((entry) => entry.bullets.length > 0) ? (
          <fieldset key={section.key} className="flex flex-col gap-3">
            <legend className="mb-2 text-sm font-semibold text-ink">{section.title}</legend>
            {section.entries.map((entry, entryIndex) =>
              entry.bullets.length > 0 ? (
                <Field
                  key={`${entry.ref}-${entry.title}`}
                  id={`edit-${section.key}-${entryIndex}`}
                  label={[entry.title, entry.subtitle].filter(Boolean).join(" · ")}
                  hint={t("workshop.edit.bulletsHint")}
                >
                  <Textarea
                    id={`edit-${section.key}-${entryIndex}`}
                    rows={Math.max(2, entry.bullets.length + 1)}
                    value={entry.bullets.join("\n")}
                    onChange={(event) => setBullets(sectionIndex, entryIndex, event.target.value)}
                  />
                </Field>
              ) : null,
            )}
          </fieldset>
        ) : null,
      )}

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-2 text-sm font-semibold text-ink">{t("workshop.edit.letter")}</legend>
        <Field id="edit-subject" label={t("workshop.edit.letterSubject")}>
          <Input
            id="edit-subject"
            value={draft.letter.subject}
            onChange={(event) => setLetter({ subject: event.target.value })}
          />
        </Field>
        {draft.letter.paragraphs.map((paragraph, index) => (
          <Field
            // Paragraphs have no id; their position is stable while editing.
            key={index}
            id={`edit-paragraph-${index}`}
            label={t("workshop.edit.paragraph", { number: index + 1 })}
          >
            <Textarea
              id={`edit-paragraph-${index}`}
              rows={5}
              value={paragraph}
              onChange={(event) =>
                setLetter({
                  paragraphs: draft.letter.paragraphs.map((p, i) =>
                    i === index ? event.target.value : p,
                  ),
                })
              }
            />
          </Field>
        ))}
      </fieldset>

      {update.error ? (
        <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
          {update.error.message || t("errors.generic")}
        </p>
      ) : null}
      <Button className="self-start" onClick={save} disabled={update.isPending}>
        {update.isPending ? (
          <LoaderCircle className="animate-spin" aria-hidden="true" />
        ) : (
          <RefreshCw aria-hidden="true" />
        )}
        {t("workshop.edit.regenerate")}
      </Button>
    </div>
  );
}
