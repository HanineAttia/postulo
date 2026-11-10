import { ArrowRight, CircleAlert, CircleCheck } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { type ApplicationReport, JURY_CRITERIA, type JuryReport } from "@/lib/api";
import { useDynamicT } from "@/lib/i18nKey";
import { cn } from "@/lib/utils";

function ScoreTile({
  label,
  testId,
  before,
  after,
}: {
  label: string;
  testId: string;
  before: number | null;
  after: number | null;
}) {
  const { t } = useTranslation();
  const final = after ?? before;
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4">
      <span className="text-sm text-muted">{label}</span>
      {final === null ? (
        <span className="text-sm text-muted">{t("workshop.quality.notRun")}</span>
      ) : (
        <div className="flex items-baseline gap-2" data-testid={testId}>
          {after !== null && before !== null && after !== before ? (
            <>
              <span className="tabular text-lg text-muted" data-testid={`${testId}-before`}>
                {before}
              </span>
              <ArrowRight className="size-4 self-center text-muted" aria-hidden="true" />
              <span className="sr-only">{t("workshop.quality.then")}</span>
            </>
          ) : null}
          <span className="tabular text-3xl font-semibold text-ink" data-testid={`${testId}-final`}>
            {final}
          </span>
          <span className="text-sm text-muted">/100</span>
        </div>
      )}
    </div>
  );
}

const DECISION_VARIANT = { interview: "success", maybe: "warning", reject: "danger" } as const;
const PRIORITY_VARIANT = { high: "danger", medium: "warning", low: "neutral" } as const;

function JuryDetails({ jury }: { jury: JuryReport }) {
  const { t } = useTranslation();
  const dt = useDynamicT();
  return (
    <section aria-labelledby="jury-title" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <h3 id="jury-title" className="text-base font-semibold text-ink">
          {t("workshop.quality.jury")}
        </h3>
        <Badge variant={DECISION_VARIANT[jury.decision]}>
          {dt(`workshop.quality.decisions.${jury.decision}`)}
        </Badge>
      </div>
      {jury.six_second_impression ? (
        <p className="rounded-md border-l-2 border-primary bg-primary-soft/40 px-3 py-2 text-sm">
          <span className="font-medium text-ink">{t("workshop.quality.sixSeconds")} </span>
          {jury.six_second_impression}
        </p>
      ) : null}
      <dl className="grid gap-2 sm:grid-cols-2">
        {JURY_CRITERIA.filter((key) => jury.criteria[key] !== undefined).map((key) => {
          const value = jury.criteria[key] ?? 0;
          return (
            <div key={key} className="flex items-center gap-3">
              <dt className="w-32 shrink-0 text-sm text-muted">
                {dt(`workshop.quality.criteria.${key}`)}
              </dt>
              <dd className="flex flex-1 items-center gap-2">
                <Progress value={value * 10} aria-label={dt(`workshop.quality.criteria.${key}`)} />
                <span className="tabular w-10 text-right text-sm text-ink">{value}/10</span>
              </dd>
            </div>
          );
        })}
      </dl>
      {jury.strengths.length > 0 ? (
        <div className="flex flex-col gap-1">
          <h4 className="text-sm font-medium text-ink">{t("workshop.quality.strengths")}</h4>
          <ul className="list-disc pl-5 text-sm text-ink">
            {jury.strengths.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {jury.corrections.length > 0 ? (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-medium text-ink">{t("workshop.quality.corrections")}</h4>
          <ul className="flex flex-col gap-1.5">
            {jury.corrections.map((item) => (
              <li key={`${item.priority}-${item.text}`} className="flex items-start gap-2 text-sm">
                <Badge variant={PRIORITY_VARIANT[item.priority]}>
                  {dt(`workshop.quality.priorities.${item.priority}`)}
                </Badge>
                <span className="text-ink">{item.text}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

export function QualityPanel({ report }: { report: ApplicationReport }) {
  const { t } = useTranslation();
  const dt = useDynamicT();
  const ats = report.ats;
  const jury = report.jury_after ?? report.jury_before;
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <ScoreTile
          label={t("workshop.quality.juryScore")}
          testId="jury-score"
          before={report.jury_before?.score ?? null}
          after={report.jury_after?.score ?? null}
        />
        <ScoreTile
          label={t("workshop.quality.atsScore")}
          testId="ats-score"
          before={report.ats_before?.score ?? null}
          after={ats?.score ?? null}
        />
      </div>
      {report.revision_applied ? (
        <p className="text-sm text-muted">
          {report.revision_kept
            ? t("workshop.quality.revisionKept")
            : t("workshop.quality.revisionDropped")}
        </p>
      ) : null}

      {jury ? <JuryDetails jury={jury} /> : null}

      {ats ? (
        <section aria-labelledby="ats-title" className="flex flex-col gap-4">
          <h3 id="ats-title" className="text-base font-semibold text-ink">
            {t("workshop.quality.ats")}
          </h3>
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {ats.checks.map((check) => {
              const Icon = check.ok ? CircleCheck : CircleAlert;
              return (
                <li key={check.key} className="flex items-start gap-2 text-sm">
                  <Icon
                    className={cn("mt-0.5 size-4 shrink-0", check.ok ? "text-success" : "text-danger")}
                    aria-hidden="true"
                  />
                  <span>
                    <span className="text-ink">{dt(`workshop.ats.${check.key}`)}</span>
                    <span className="sr-only">
                      {" "}
                      {check.ok ? t("workshop.quality.ok") : t("workshop.quality.failed")}
                    </span>
                    {check.detail ? <span className="block text-muted">{check.detail}</span> : null}
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="flex flex-col gap-2">
            <h4 className="text-sm font-medium text-ink">
              {t("workshop.quality.keywordsFound", { count: ats.keywords_found.length })}
            </h4>
            <div className="flex flex-wrap gap-1.5" data-testid="keywords-found">
              {ats.keywords_found.map((word) => (
                <Badge key={word} variant="success">
                  {word}
                </Badge>
              ))}
            </div>
            <h4 className="text-sm font-medium text-ink">
              {t("workshop.quality.keywordsMissing", { count: ats.keywords_missing.length })}
            </h4>
            <div className="flex flex-wrap gap-1.5" data-testid="keywords-missing">
              {ats.keywords_missing.map((word) => (
                <Badge key={word} variant="warning">
                  {word}
                </Badge>
              ))}
            </div>
          </div>
          <details className="rounded-lg border border-border">
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-ink">
              {t("workshop.quality.atsText")}
            </summary>
            <pre className="max-h-96 overflow-auto px-3 pb-3 font-sans text-xs whitespace-pre-wrap text-ink">
              {ats.text}
            </pre>
          </details>
        </section>
      ) : null}
    </div>
  );
}
