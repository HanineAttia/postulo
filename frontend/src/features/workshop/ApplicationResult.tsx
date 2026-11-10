import { useMutation } from "@tanstack/react-query";
import {
  CircleAlert,
  Download,
  FolderOpen,
  LoaderCircle,
  Mail,
  Save,
  Send,
  TriangleAlert,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api, type ApplicationDetail } from "@/lib/api";
import { useDynamicT } from "@/lib/i18nKey";

import { EditPanel } from "./EditPanel";
import { QualityPanel } from "./QualityPanel";
import { useApplication, useMarkSent, useUpdateDocuments } from "./useApplications";

type ResultTab = "documents" | "quality" | "email" | "advice" | "edit";

export function ApplicationResult({ id }: { id: string }) {
  const { t } = useTranslation();
  const query = useApplication(id);
  const [tab, setTab] = useState<ResultTab>("documents");

  if (query.isPending) {
    return (
      <div className="flex flex-col gap-4" aria-busy="true">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-[480px] w-full" />
      </div>
    );
  }
  if (query.isError) {
    return (
      <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
        {query.error.message || t("errors.server")}
      </p>
    );
  }
  const detail = query.data;
  return (
    <Card aria-labelledby="application-title">
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <CardTitle id="application-title">
            {detail.position || t("workshop.result.untitled")}
          </CardTitle>
          <p className="text-sm text-muted">
            {[detail.organization, new Date(detail.created_at).toLocaleDateString()]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <SentButton detail={detail} />
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {detail.report.warnings.length > 0 ? (
          <div
            role="status"
            className="flex flex-col gap-1 rounded-md bg-warning-soft px-3 py-2 text-sm text-warning"
          >
            <span className="flex items-center gap-2 font-medium">
              <TriangleAlert className="size-4" aria-hidden="true" />
              {t("workshop.result.warnings", { count: detail.report.warnings.length })}
            </span>
            <ul className="list-disc pl-6" data-testid="warnings">
              {detail.report.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <Tabs value={tab} onValueChange={(value) => setTab(value as ResultTab)}>
          <TabsList aria-label={t("workshop.result.tabsLabel")}>
            <TabsTrigger value="documents">{t("workshop.result.tabs.documents")}</TabsTrigger>
            <TabsTrigger value="quality">{t("workshop.result.tabs.quality")}</TabsTrigger>
            <TabsTrigger value="email">{t("workshop.result.tabs.email")}</TabsTrigger>
            <TabsTrigger value="advice">{t("workshop.result.tabs.advice")}</TabsTrigger>
            <TabsTrigger value="edit">{t("workshop.result.tabs.edit")}</TabsTrigger>
          </TabsList>
          <TabsContent value="documents">
            <DocumentsPanel detail={detail} />
          </TabsContent>
          <TabsContent value="quality">
            <QualityPanel report={detail.report} />
          </TabsContent>
          <TabsContent value="email">
            <EmailPanel key={detail.updated_at} detail={detail} />
          </TabsContent>
          <TabsContent value="advice">
            <AdvicePanel detail={detail} />
          </TabsContent>
          <TabsContent value="edit">
            {detail.documents ? (
              <EditPanel
                key={detail.updated_at}
                detail={detail}
                documents={detail.documents}
                onDone={() => setTab("documents")}
              />
            ) : null}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function SentButton({ detail }: { detail: ApplicationDetail }) {
  const { t } = useTranslation();
  const sent = useMarkSent(detail.id);
  if (detail.status !== "draft") {
    return (
      <Badge variant="success">
        <Send aria-hidden="true" />
        {detail.sent_at
          ? t("workshop.result.sentOn", { date: new Date(detail.sent_at).toLocaleDateString() })
          : t("workshop.result.sent")}
      </Badge>
    );
  }
  return (
    <Button
      variant="outline"
      onClick={() =>
        sent.mutate(undefined, { onSuccess: () => toast.success(t("workshop.result.sentToast")) })
      }
      disabled={sent.isPending}
    >
      <Send aria-hidden="true" />
      {t("workshop.result.markSent")}
    </Button>
  );
}

function DocumentsPanel({ detail }: { detail: ApplicationDetail }) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<"cv" | "letter">("cv");
  const openFolder = useMutation({ mutationFn: () => api.openFolder(detail.id) });
  const url = detail.files[kind];
  const report = detail.report;
  // The query string changes after each regeneration, so the preview reloads.
  const version = encodeURIComponent(detail.updated_at + String(report.ats?.score ?? ""));
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label={t("workshop.documents.choose")} className="flex gap-1">
          {(["cv", "letter"] as const).map((value) => (
            <Button
              key={value}
              size="sm"
              variant={kind === value ? "subtle" : "ghost"}
              aria-pressed={kind === value}
              onClick={() => setKind(value)}
            >
              {t(`workshop.documents.${value}`)}
            </Button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          {url ? (
            <Button variant="outline" size="sm" asChild>
              <a href={`${url}?download=true`} download>
                <Download aria-hidden="true" />
                {t("workshop.documents.download")}
              </a>
            </Button>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            onClick={() => openFolder.mutate()}
            disabled={openFolder.isPending}
          >
            <FolderOpen aria-hidden="true" />
            {t("workshop.documents.openFolder")}
          </Button>
        </div>
      </div>
      <p className="text-sm text-muted" data-testid="document-facts">
        {t("workshop.documents.facts", {
          pages: kind === "cv" ? report.pages : report.letter_pages,
          level: report.compaction_level,
          engine: report.engine === "typst" ? "Typst" : "HTML",
        })}
      </p>
      {openFolder.error ? (
        <p role="alert" className="text-sm text-danger">
          {openFolder.error.message}
        </p>
      ) : null}
      {url ? (
        <iframe
          title={t(`workshop.documents.${kind}`)}
          src={`${url}?v=${version}`}
          className="h-[780px] w-full rounded-lg border border-border bg-surface"
          data-testid="pdf-preview"
        />
      ) : (
        <p className="flex items-center gap-2 text-sm text-danger">
          <CircleAlert className="size-4" aria-hidden="true" />
          {t("workshop.documents.missing")}
        </p>
      )}
    </div>
  );
}

function EmailPanel({ detail }: { detail: ApplicationDetail }) {
  const { t } = useTranslation();
  const [subject, setSubject] = useState(detail.email_subject);
  const [body, setBody] = useState(detail.email_body);
  const update = useUpdateDocuments(detail.id);
  const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  const words = body.trim() ? body.trim().split(/\s+/).length : 0;
  return (
    <div className="flex flex-col gap-3">
      <Field id="email-subject" label={t("workshop.email.subject")}>
        <Input id="email-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
      </Field>
      <Field
        id="email-body"
        label={t("workshop.email.body")}
        hint={t("workshop.email.words", { count: words })}
      >
        <Textarea
          id="email-body"
          rows={12}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          aria-describedby="email-body-hint"
        />
      </Field>
      <p className="text-sm text-muted">{t("workshop.email.attachments")}</p>
      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <a href={mailto}>
            <Mail aria-hidden="true" />
            {t("workshop.email.open")}
          </a>
        </Button>
        {detail.documents ? (
          <Button
            variant="outline"
            disabled={update.isPending}
            onClick={() =>
              detail.documents &&
              update.mutate(
                { documents: detail.documents, email_subject: subject, email_body: body },
                { onSuccess: () => toast.success(t("workshop.email.saved")) },
              )
            }
          >
            {update.isPending ? (
              <LoaderCircle className="animate-spin" aria-hidden="true" />
            ) : (
              <Save aria-hidden="true" />
            )}
            {t("workshop.email.save")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function AdvicePanel({ detail }: { detail: ApplicationDetail }) {
  const { t } = useTranslation();
  const dt = useDynamicT();
  const { tips, gaps, removed_skills: removed } = detail.report;
  const blocks = [
    { key: "tips", items: tips },
    { key: "gaps", items: gaps },
    { key: "removedSkills", items: removed },
  ].filter((block) => block.items.length > 0);
  if (blocks.length === 0) {
    return <p className="text-sm text-muted">{t("workshop.advice.empty")}</p>;
  }
  return (
    <div className="flex flex-col gap-5">
      {blocks.map((block) => (
        <section key={block.key} className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-ink">{dt(`workshop.advice.${block.key}`)}</h3>
          <ul className="list-disc pl-5 text-sm text-ink">
            {block.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
