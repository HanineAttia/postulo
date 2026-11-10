import { CalendarCheck, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoJobCard } from "@/features/jobs/DemoJobCard";
import { CompletenessCard } from "@/features/profile/CompletenessCard";
import { useProfile } from "@/features/profile/useProfile";

export function DashboardPage() {
  const { t } = useTranslation();
  const profile = useProfile();
  const hasProfile = (profile.data?.version ?? 0) > 0;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("dashboard.title")}</h1>
        <p className="text-sm text-muted">{t("dashboard.subtitle")}</p>
      </div>

      {hasProfile ? null : (
      <EmptyState
        icon={Sparkles}
        title={t("dashboard.empty.title")}
        description={t("dashboard.empty.description")}
        action={
          <Button asChild>
            <Link to="/profile">{t("dashboard.empty.action")}</Link>
          </Button>
        }
      />
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          {hasProfile ? <CompletenessCard /> : null}
          <DemoJobCard />
        </div>
        <Card aria-labelledby="today-title">
          <CardHeader>
            <CardTitle id="today-title">{t("dashboard.today.title")}</CardTitle>
          </CardHeader>
          <CardContent className="flex items-start gap-3 text-sm text-muted">
            <CalendarCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <p>{t("dashboard.today.empty")}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
