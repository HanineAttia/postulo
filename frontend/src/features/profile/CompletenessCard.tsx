import { ArrowRight, Gauge } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useDynamicT } from "@/lib/i18nKey";

import { useCompleteness } from "./useProfile";

/** Completeness score and the most valuable advice, each linking to the right tab. */
export function CompletenessCard({ limit = 4 }: { limit?: number }) {
  const { t } = useTranslation();
  const td = useDynamicT();
  const { data, isPending, isError } = useCompleteness();
  return (
    <Card aria-labelledby="completeness-title">
      <CardHeader>
        <CardTitle id="completeness-title" className="flex items-center gap-2">
          <Gauge className="size-4 text-primary" aria-hidden="true" />
          {t("completeness.title")}
        </CardTitle>
        <CardDescription>{t("completeness.description")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : isError || !data ? (
          <p className="text-sm text-danger">{t("errors.server")}</p>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <span className="tabular text-2xl font-semibold text-ink" data-testid="completeness-score">
                {data.score}
              </span>
              <span className="text-sm text-muted">/ 100</span>
              <Progress
                value={data.score}
                className="flex-1"
                aria-label={t("completeness.title")}
              />
            </div>
            {data.advice.length === 0 ? (
              <p className="text-sm text-success">{t("completeness.complete")}</p>
            ) : (
              <ul className="flex flex-col gap-1">
                {data.advice.slice(0, limit).map((advice) => (
                  <li key={advice.key}>
                    <Link
                      to={`/profile?tab=${advice.section}`}
                      className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink hover:bg-surface focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <span className="flex-1">
                        {td(`completeness.advice.${advice.key}`, advice.params)}
                      </span>
                      <span className="tabular text-xs text-muted">+{advice.points}</span>
                      <ArrowRight
                        className="size-4 text-muted group-hover:text-primary"
                        aria-hidden="true"
                      />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
