import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle, Plus, Save, Trash2, Undo2 } from "lucide-react";
import type * as React from "react";
import { useEffect, useState } from "react";
import {
  type FieldErrors,
  FormProvider,
  useFieldArray,
  useForm,
  useFormContext,
} from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useBlocker, useSearchParams } from "react-router";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, type StoredProfile } from "@/lib/api";
import { useDynamicT } from "@/lib/i18nKey";

import { BackupPanel } from "./BackupPanel";
import { BoundField, FieldGrid } from "./fields";
import { ImportCvPanel } from "./ImportCvPanel";
import { ItemSectionEditor } from "./ItemSectionEditor";
import { type CareerProfile, careerProfileSchema, cleanLines, newId } from "./schema";
import {
  IDENTITY_FIELDS,
  OBJECTIVE_FIELDS,
  PROFILE_TABS,
  type ProfileTab,
  TAB_OF_KEY,
} from "./sections";
import { useSaveProfile } from "./useProfile";

function isTab(value: string | null): value is ProfileTab {
  return value !== null && (PROFILE_TABS as readonly string[]).includes(value);
}

function errorsPerTab(errors: FieldErrors<CareerProfile>): Partial<Record<ProfileTab, number>> {
  const counts: Partial<Record<ProfileTab, number>> = {};
  for (const key of Object.keys(errors)) {
    const tab = TAB_OF_KEY[key];
    if (tab) counts[tab] = (counts[tab] ?? 0) + 1;
  }
  return counts;
}

interface ProfileEditorProps {
  stored: StoredProfile;
  onReload: () => Promise<StoredProfile | undefined>;
}

/** The "Mon parcours" editor: one form shared by every tab, saved as a whole. */
export function ProfileEditor({ stored, onReload }: ProfileEditorProps) {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("tab");
  const tab: ProfileTab = isTab(requested) ? requested : stored.version === 0 ? "import" : "identity";
  const [version, setVersion] = useState(stored.version);
  const form = useForm<CareerProfile>({
    resolver: zodResolver(careerProfileSchema),
    defaultValues: stored.profile,
    mode: "onBlur",
  });
  const { isDirty, errors } = form.formState;
  const save = useSaveProfile();
  const tabErrors = errorsPerTab(errors);

  const loadStored = (next: StoredProfile) => {
    setVersion(next.version);
    form.reset(next.profile);
  };

  // Unsaved changes: warn before leaving the page or the app route.
  useEffect(() => {
    if (!isDirty) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty]);
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      isDirty && currentLocation.pathname !== nextLocation.pathname,
  );
  useEffect(() => {
    if (blocker.state !== "blocked") return;
    if (window.confirm(t("profile.leaveConfirm"))) blocker.proceed();
    else blocker.reset();
  }, [blocker, t]);

  const onSubmit = form.handleSubmit(
    (values) =>
      save.mutate(
        { version, profile: cleanLines(values) },
        {
          onSuccess: (saved) => {
            loadStored(saved);
            toast.success(t("profile.saved"));
          },
          onError: (error) => {
            if (error instanceof ApiError && error.status === 409) {
              toast.error(error.message, {
                action: {
                  label: t("profile.reload"),
                  onClick: () => void onReload().then((fresh) => fresh && loadStored(fresh)),
                },
              });
            } else toast.error(error.message || t("errors.generic"));
          },
        },
      ),
    () => toast.error(t("profile.fixErrors")),
  );

  return (
    <FormProvider {...form}>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-6 pb-24">
        <Tabs
          value={tab}
          onValueChange={(value) => setSearchParams({ tab: value }, { replace: true })}
        >
          <TabsList aria-label={t("profile.tabsLabel")}>
            {PROFILE_TABS.map((value) => (
              <TabsTrigger key={value} value={value}>
                {t(`profile.tabs.${value}`)}
                {tabErrors[value] ? (
                  <Badge variant="danger" aria-label={t("profile.tabErrors", { count: tabErrors[value] })}>
                    {tabErrors[value]}
                  </Badge>
                ) : null}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="import">
            <ImportCvPanel blocked={isDirty} onApplied={loadStored} />
          </TabsContent>
          <TabsContent value="identity">
            <IdentityTab />
          </TabsContent>
          <TabsContent value="objective">
            <SimpleCard section="objective">
              <FieldGrid prefix="objective" specs={OBJECTIVE_FIELDS} labelPrefix="profile.fields.objective" />
            </SimpleCard>
          </TabsContent>
          {(["education", "experiences", "projects"] as const).map((section) => (
            <TabsContent key={section} value={section}>
              <ItemSectionEditor section={section} />
            </TabsContent>
          ))}
          <TabsContent value="skills" className="flex flex-col gap-6">
            <ItemSectionEditor section="skills" />
            <ItemSectionEditor section="languages" />
          </TabsContent>
          <TabsContent value="certifications" className="flex flex-col gap-6">
            <ItemSectionEditor section="certifications" />
            <ItemSectionEditor section="awards" />
          </TabsContent>
          <TabsContent value="engagements" className="flex flex-col gap-6">
            <ItemSectionEditor section="volunteering" />
            <ItemSectionEditor section="publications" />
            <SimpleCard section="more">
              <FieldGrid
                prefix=""
                specs={[
                  { name: "interests", kind: "lines", wide: true, hint: "profile.hints.lines" },
                  { name: "extra_facts", kind: "lines", wide: true, hint: "profile.hints.extraFacts" },
                ]}
                labelPrefix="profile.fields.main"
              />
            </SimpleCard>
          </TabsContent>
          <TabsContent value="backup">
            <BackupPanel
              hasContent={stored.version > 0}
              blocked={isDirty}
              onApplied={loadStored}
            />
          </TabsContent>
        </Tabs>

        {isDirty || save.isPending ? (
          <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface-raised/95 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-end gap-3 px-8 py-3">
              <span className="mr-auto text-sm text-muted" role="status">
                {t("profile.unsaved")}
              </span>
              <Button
                type="button"
                variant="ghost"
                onClick={() => form.reset()}
                disabled={save.isPending}
              >
                <Undo2 aria-hidden="true" />
                {t("profile.discard")}
              </Button>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? (
                  <LoaderCircle className="animate-spin" aria-hidden="true" />
                ) : (
                  <Save aria-hidden="true" />
                )}
                {t("profile.save")}
              </Button>
            </div>
          </div>
        ) : null}
      </form>
    </FormProvider>
  );
}

function SimpleCard({ section, children }: { section: string; children: React.ReactNode }) {
  const td = useDynamicT();
  const titleId = `section-${section}-title`;
  return (
    <Card aria-labelledby={titleId}>
      <CardHeader>
        <CardTitle id={titleId}>{td(`profile.sections.${section}.title`)}</CardTitle>
        <CardDescription>{td(`profile.sections.${section}.description`)}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function IdentityTab() {
  return (
    <div className="flex flex-col gap-6">
      <SimpleCard section="identity">
        <FieldGrid prefix="identity" specs={IDENTITY_FIELDS} labelPrefix="profile.fields.identity" />
      </SimpleCard>
      <SimpleCard section="pitch">
        <div className="grid gap-4">
          <BoundField path="headline" spec={{ name: "headline", kind: "text" }} labelPrefix="profile.fields.main" />
          <BoundField
            path="summary"
            spec={{ name: "summary", kind: "textarea", hint: "profile.hints.summary" }}
            labelPrefix="profile.fields.main"
          />
        </div>
      </SimpleCard>
      <LinksCard />
    </div>
  );
}

function LinksCard() {
  const { t } = useTranslation();
  const { control } = useFormContext<CareerProfile>();
  const { fields, append, remove } = useFieldArray({
    control,
    name: "identity.links",
    keyName: "fieldKey",
  });
  return (
    <SimpleCard section="links">
      <div className="flex flex-col gap-3">
        {fields.map((field, index) => (
          <div key={field.fieldKey} className="flex items-end gap-2">
            <div className="grid flex-1 gap-4 sm:grid-cols-2">
              <BoundField
                path={`identity.links.${index}.label`}
                spec={{ name: "label", kind: "text" }}
                labelPrefix="profile.fields.links"
              />
              <BoundField
                path={`identity.links.${index}.url`}
                spec={{ name: "url", kind: "url" }}
                labelPrefix="profile.fields.links"
              />
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => remove(index)}
              aria-label={t("profile.removeLink")}
            >
              <Trash2 aria-hidden="true" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => append({ id: newId(), label: "", url: null })}
        >
          <Plus aria-hidden="true" />
          {t("profile.addLink")}
        </Button>
      </div>
    </SimpleCard>
  );
}
