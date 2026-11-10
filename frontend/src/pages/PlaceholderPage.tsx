import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EmptyState } from "@/components/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import type { NavItem } from "../app/navigation";

type PlaceholderKey = Exclude<NavItem["key"], "dashboard">;

const ACTION_TARGET: Record<PlaceholderKey, string> = {
  offers: "/profile",
  hiddenMarket: "/profile",
  organizations: "/profile",
  workshop: "/",
  tracking: "/",
  network: "/profile",
  coach: "/profile",
  profile: "/",
  settings: "/",
};

/** Page shell for features delivered in later phases: explains the page, offers a next step. */
export function PlaceholderPage({ item }: { item: NavItem & { key: PlaceholderKey } }) {
  const { t } = useTranslation();
  return (
    <EmptyState
      headingLevel="h1"
      icon={item.icon}
      title={t(`pages.${item.key}.title`)}
      description={t(`pages.${item.key}.description`)}
      badge={<Badge variant="neutral">{t("pages.comingSoon", { phase: item.phase })}</Badge>}
      action={
        <Button variant="outline" asChild>
          <Link to={ACTION_TARGET[item.key]}>{t(`pages.${item.key}.action`)}</Link>
        </Button>
      }
      className="py-20"
    />
  );
}
