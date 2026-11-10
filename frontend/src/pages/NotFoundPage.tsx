import { MapPinOff } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <EmptyState
      headingLevel="h1"
      icon={MapPinOff}
      title={t("notFound.title")}
      description={t("notFound.description")}
      action={
        <Button variant="outline" asChild>
          <Link to="/">{t("notFound.action")}</Link>
        </Button>
      }
      className="py-20"
    />
  );
}
