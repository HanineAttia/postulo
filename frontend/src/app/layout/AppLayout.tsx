import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet } from "react-router";

import { useSettings } from "@/features/settings/useSettings";

import { readPreference, writePreference } from "@/lib/preferences";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(() => readPreference("sidebar") === "collapsed");
  const settings = useSettings();

  const toggle = () => {
    setCollapsed((value) => {
      writePreference("sidebar", value ? "expanded" : "collapsed");
      return !value;
    });
  };

  // First launch: the onboarding wizard comes first (it can be skipped in one click).
  if (settings.data && !settings.data.onboarding_completed) return <Navigate to="/welcome" replace />;

  return (
    <div className="flex min-h-screen bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
      >
        {t("app.skipToContent")}
      </a>
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main id="main" tabIndex={-1} className="flex-1 px-8 py-8 outline-none">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
