import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  FileText,
  LoaderCircle,
  PenLine,
  Rss,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { EmptyState } from "@/components/EmptyState";
import { LogoMark } from "@/components/Logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FieldGrid } from "@/features/profile/fields";
import { ImportCvPanel } from "@/features/profile/ImportCvPanel";
import { type CareerProfile, careerProfileSchema, cleanLines } from "@/features/profile/schema";
import { OBJECTIVE_FIELDS } from "@/features/profile/sections";
import { useLoadSample, useProfile, useSaveProfile } from "@/features/profile/useProfile";
import { AIProviderForm } from "@/features/settings/AIProviderForm";
import { toSettings, useSaveSettings, useSettings } from "@/features/settings/useSettings";
import type { StoredProfile } from "@/lib/api";
import { cn } from "@/lib/utils";

const STEPS = ["ai", "profile", "objective", "sources", "organizations"] as const;
type Step = (typeof STEPS)[number];

/** First-launch wizard in 5 steps (SPEC 12.3). Every step can be skipped. */
export function OnboardingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const settings = useSettings();
  const saveSettings = useSaveSettings();
  const [index, setIndex] = useState(0);
  const step: Step = STEPS[index] ?? "ai";

  const finish = () => {
    if (!settings.data) return;
    saveSettings.mutate(
      { ...toSettings(settings.data), onboarding_completed: true },
      {
        onSuccess: () => void navigate("/"),
        onError: (error) => toast.error(error.message || t("errors.generic")),
      },
    );
  };
  const next = () => (index < STEPS.length - 1 ? setIndex(index + 1) : finish());

  return (
    <div className="min-h-screen bg-surface px-6 py-10">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-8">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <LogoMark />
            <div>
              <h1 className="text-xl font-semibold text-ink">{t("onboarding.title")}</h1>
              <p className="text-sm text-muted">{t("onboarding.subtitle")}</p>
            </div>
          </div>
          <Button variant="ghost" onClick={finish} disabled={saveSettings.isPending}>
            {t("onboarding.skipAll")}
          </Button>
        </header>

        <ol className="grid grid-cols-5 gap-2" aria-label={t("onboarding.stepsLabel")}>
          {STEPS.map((value, position) => (
            <li key={value} aria-current={position === index ? "step" : undefined}>
              <button
                type="button"
                onClick={() => setIndex(position)}
                className="flex w-full flex-col gap-2 rounded-md text-left focus-visible:outline-2 focus-visible:outline-ring"
              >
                <span
                  className={cn(
                    "h-1.5 rounded-full",
                    position <= index ? "bg-primary" : "bg-border",
                  )}
                  aria-hidden="true"
                />
                <span
                  className={cn(
                    "flex items-center gap-1 text-xs",
                    position === index ? "font-medium text-ink" : "text-muted",
                  )}
                >
                  {position < index ? <Check className="size-3" aria-hidden="true" /> : null}
                  {position + 1}. {t(`onboarding.steps.${value}.short`)}
                </span>
              </button>
            </li>
          ))}
        </ol>

        <Card aria-labelledby="onboarding-step-title">
          <CardHeader>
            <CardTitle id="onboarding-step-title">{t(`onboarding.steps.${step}.title`)}</CardTitle>
            <CardDescription>{t(`onboarding.steps.${step}.description`)}</CardDescription>
          </CardHeader>
          <CardContent>
            {step === "ai" ? <AIProviderForm /> : null}
            {step === "profile" ? <ProfileStep onDone={next} /> : null}
            {step === "objective" ? <ObjectiveStep onDone={next} /> : null}
            {step === "sources" ? <ComingSoonStep icon={Rss} step="sources" /> : null}
            {step === "organizations" ? (
              <ComingSoonStep icon={Building2} step="organizations" />
            ) : null}
          </CardContent>
        </Card>

        <nav className="flex items-center justify-between" aria-label={t("onboarding.navLabel")}>
          <Button
            variant="ghost"
            onClick={() => setIndex(Math.max(0, index - 1))}
            disabled={index === 0}
          >
            <ArrowLeft aria-hidden="true" />
            {t("onboarding.back")}
          </Button>
          {step !== "objective" ? (
            <Button onClick={next} disabled={saveSettings.isPending}>
              {index === STEPS.length - 1 ? t("onboarding.finish") : t("onboarding.next")}
              {index === STEPS.length - 1 ? (
                <Check aria-hidden="true" />
              ) : (
                <ArrowRight aria-hidden="true" />
              )}
            </Button>
          ) : null}
        </nav>
      </div>
    </div>
  );
}

function ProfileStep({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [choice, setChoice] = useState<"import" | null>(null);
  const sample = useLoadSample();
  if (choice === "import") return <ImportCvPanel blocked={false} onApplied={onDone} />;
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <ChoiceButton
        icon={FileText}
        title={t("onboarding.profile.import")}
        description={t("onboarding.profile.importHint")}
        onClick={() => setChoice("import")}
      />
      <ChoiceButton
        icon={PenLine}
        title={t("onboarding.profile.forms")}
        description={t("onboarding.profile.formsHint")}
        onClick={onDone}
      />
      <ChoiceButton
        icon={Sparkles}
        title={t("onboarding.profile.sample")}
        description={t("onboarding.profile.sampleHint")}
        busy={sample.isPending}
        onClick={() =>
          sample.mutate(false, {
            onSuccess: () => {
              toast.success(t("backup.sampleLoaded"));
              onDone();
            },
            onError: (error) => toast.error(error.message || t("errors.generic")),
          })
        }
      />
    </div>
  );
}

function ChoiceButton({
  icon: Icon,
  title,
  description,
  busy,
  onClick,
}: {
  icon: typeof FileText;
  title: string;
  description: string;
  busy?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="flex flex-col items-start gap-2 rounded-lg border border-border p-4 text-left transition-colors hover:border-primary hover:bg-primary-soft focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-60"
    >
      {busy ? (
        <LoaderCircle className="size-5 animate-spin text-primary" aria-hidden="true" />
      ) : (
        <Icon className="size-5 text-primary" aria-hidden="true" />
      )}
      <span className="text-sm font-medium text-ink">{title}</span>
      <span className="text-xs text-muted">{description}</span>
    </button>
  );
}

function ObjectiveStep({ onDone }: { onDone: () => void }) {
  const profile = useProfile();
  if (profile.isPending) return <Skeleton className="h-48 w-full" />;
  if (profile.isError) return null;
  return <ObjectiveForm stored={profile.data} onDone={onDone} />;
}

function ObjectiveForm({ stored, onDone }: { stored: StoredProfile; onDone: () => void }) {
  const { t } = useTranslation();
  const save = useSaveProfile();
  const form = useForm<CareerProfile>({
    resolver: zodResolver(careerProfileSchema),
    defaultValues: stored.profile,
  });
  const submit = form.handleSubmit((values) => {
    if (!form.formState.isDirty) {
      onDone();
      return;
    }
    save.mutate(
      { version: stored.version, profile: cleanLines(values) },
      {
        onSuccess: () => {
          toast.success(t("profile.saved"));
          onDone();
        },
        onError: (error) => toast.error(error.message || t("errors.generic")),
      },
    );
  });
  return (
    <FormProvider {...form}>
      <form onSubmit={submit} noValidate className="flex flex-col gap-6">
        <FieldGrid prefix="objective" specs={OBJECTIVE_FIELDS} labelPrefix="profile.fields.objective" />
        <Button type="submit" className="self-end" disabled={save.isPending}>
          {save.isPending ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : null}
          {t("onboarding.saveAndContinue")}
          <ArrowRight aria-hidden="true" />
        </Button>
      </form>
    </FormProvider>
  );
}

function ComingSoonStep({ icon, step }: { icon: typeof Rss; step: "sources" | "organizations" }) {
  const { t } = useTranslation();
  return (
    <EmptyState
      icon={icon}
      title={t(`onboarding.steps.${step}.soonTitle`)}
      description={t(`onboarding.steps.${step}.soonDescription`)}
      badge={<Badge>{t("pages.comingSoon", { phase: 3 })}</Badge>}
    />
  );
}
