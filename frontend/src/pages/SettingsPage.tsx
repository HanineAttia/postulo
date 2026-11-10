import { Compass } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AIProviderForm } from "@/features/settings/AIProviderForm";

export function SettingsPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("settings.title")}</h1>
        <p className="text-sm text-muted">{t("settings.subtitle")}</p>
      </div>
      <Card aria-labelledby="settings-ai-title">
        <CardHeader>
          <CardTitle id="settings-ai-title">{t("settings.ai.title")}</CardTitle>
          <CardDescription>{t("settings.ai.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <AIProviderForm />
        </CardContent>
      </Card>
      <Card aria-labelledby="settings-more-title">
        <CardHeader>
          <CardTitle id="settings-more-title">{t("settings.more.title")}</CardTitle>
          <CardDescription>{t("settings.more.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" asChild>
            <Link to="/welcome">
              <Compass aria-hidden="true" />
              {t("settings.more.onboarding")}
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
