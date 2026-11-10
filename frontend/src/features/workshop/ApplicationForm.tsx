import { useMutation } from "@tanstack/react-query";
import { FileText, LoaderCircle, Sparkles } from "lucide-react";
import { type FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useSettings } from "@/features/settings/useSettings";
import {
  ApiError,
  api,
  type DocLang,
  type DocumentSettings,
  type Job,
  type TemplateName,
} from "@/lib/api";

/** Same minimum as the server: a full offer, not a title. */
export const MIN_OFFER_CHARS = 80;

const FALLBACK_DEFAULTS: DocumentSettings = {
  engine: "typst",
  template: "modern",
  language: "fr",
  jury: true,
  revision: true,
  threshold: 82,
};

interface ApplicationFormProps {
  onStarted: (job: Job) => void;
  /** Disable the submit button while a job runs. */
  busy: boolean;
}

/** Left panel of the workshop: the offer and the generation options (SPEC 12.3). */
export function ApplicationForm(props: ApplicationFormProps) {
  const settings = useSettings();
  if (settings.isPending) return <Skeleton className="h-96 w-full" />;
  return <OfferForm {...props} defaults={settings.data?.documents ?? FALLBACK_DEFAULTS} />;
}

function OfferForm({
  onStarted,
  busy,
  defaults,
}: ApplicationFormProps & { defaults: DocumentSettings }) {
  const { t } = useTranslation();

  const [offer, setOffer] = useState("");
  const [organization, setOrganization] = useState("");
  const [position, setPosition] = useState("");
  const [lang, setLang] = useState<DocLang>(defaults.language);
  const [template, setTemplate] = useState<TemplateName>(defaults.template);
  const [jury, setJury] = useState(defaults.jury);
  const [revision, setRevision] = useState(defaults.revision);
  const [threshold, setThreshold] = useState(defaults.threshold);
  const [tooShort, setTooShort] = useState(false);

  const sample = useMutation({
    mutationFn: api.sampleOffer,
    onSuccess: (body) => {
      setOffer(body.text);
      setTooShort(false);
    },
  });
  const create = useMutation({ mutationFn: api.createApplication, onSuccess: onStarted });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (offer.trim().length < MIN_OFFER_CHARS) {
      setTooShort(true);
      return;
    }
    create.mutate({
      offer_text: offer,
      organization: organization.trim(),
      position: position.trim(),
      lang,
      template,
      jury,
      revision: jury && revision,
      threshold,
    });
  };

  const error = create.error;
  const emptyProfile = error instanceof ApiError && error.status === 409;

  return (
    <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
      <Field
        id="offer-text"
        label={t("workshop.form.offer")}
        hint={t("workshop.form.offerHint")}
        error={tooShort ? "workshop.form.offerTooShort" : undefined}
      >
        <Textarea
          id="offer-text"
          value={offer}
          onChange={(event) => {
            setOffer(event.target.value);
            if (tooShort) setTooShort(false);
          }}
          rows={10}
          aria-describedby={tooShort ? "offer-text-error" : "offer-text-hint"}
          aria-invalid={tooShort || undefined}
          placeholder={t("workshop.form.offerPlaceholder")}
        />
      </Field>
      <Button
        variant="ghost"
        size="sm"
        className="self-start"
        onClick={() => sample.mutate()}
        disabled={sample.isPending}
      >
        <FileText aria-hidden="true" />
        {t("workshop.form.useSample")}
      </Button>

      <div className="grid grid-cols-2 gap-3">
        <Field id="organization" label={t("workshop.form.organization")}>
          <Input
            id="organization"
            value={organization}
            onChange={(event) => setOrganization(event.target.value)}
            placeholder={t("workshop.form.detected")}
          />
        </Field>
        <Field id="position" label={t("workshop.form.position")}>
          <Input
            id="position"
            value={position}
            onChange={(event) => setPosition(event.target.value)}
            placeholder={t("workshop.form.detected")}
          />
        </Field>
        <Field id="doc-lang" label={t("workshop.form.language")}>
          <NativeSelect
            id="doc-lang"
            value={lang}
            onChange={(event) => setLang(event.target.value as DocLang)}
          >
            <option value="fr">{t("workshop.languages.fr")}</option>
            <option value="en">{t("workshop.languages.en")}</option>
          </NativeSelect>
        </Field>
        <Field id="doc-template" label={t("workshop.form.template")}>
          <NativeSelect
            id="doc-template"
            value={template}
            onChange={(event) => setTemplate(event.target.value as TemplateName)}
          >
            <option value="modern">{t("workshop.templates.modern")}</option>
            <option value="classic">{t("workshop.templates.classic")}</option>
          </NativeSelect>
        </Field>
      </div>

      <fieldset className="flex flex-col gap-2 rounded-lg border border-border p-3">
        <legend className="px-1 text-sm font-medium text-ink">{t("workshop.form.quality")}</legend>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={jury}
            onChange={(event) => setJury(event.target.checked)}
          />
          {t("workshop.form.jury")}
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={jury && revision}
            disabled={!jury}
            onChange={(event) => setRevision(event.target.checked)}
          />
          {t("workshop.form.revision")}
        </label>
        <div className="flex items-center gap-2 text-sm text-ink">
          <label htmlFor="threshold">{t("workshop.form.threshold")}</label>
          <Input
            id="threshold"
            type="number"
            min={0}
            max={100}
            className="h-8 w-20"
            value={threshold}
            disabled={!jury || !revision}
            onChange={(event) => setThreshold(Number(event.target.value))}
          />
        </div>
      </fieldset>

      {error ? (
        <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
          {error instanceof ApiError && error.status === 0
            ? t("errors.server")
            : error.message || t("errors.generic")}{" "}
          {emptyProfile ? (
            <Link to="/profile" className="font-medium underline">
              {t("workshop.form.goToProfile")}
            </Link>
          ) : null}
        </p>
      ) : null}

      <Button type="submit" size="lg" disabled={create.isPending || busy}>
        {create.isPending || busy ? (
          <LoaderCircle className="animate-spin" aria-hidden="true" />
        ) : (
          <Sparkles aria-hidden="true" />
        )}
        {t("workshop.form.submit")}
      </Button>
    </form>
  );
}
