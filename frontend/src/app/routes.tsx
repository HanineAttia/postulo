import type { RouteObject } from "react-router";

import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";

import { AppLayout } from "./layout/AppLayout";
import { NAV_ITEMS, type NavItem } from "./navigation";

/** Pages already delivered; the others show a placeholder until their phase. */
const IMPLEMENTED = ["dashboard", "profile", "settings"] as const;
type PlaceholderItem = NavItem & { key: Exclude<NavItem["key"], (typeof IMPLEMENTED)[number]> };

function isPlaceholder(item: NavItem): item is PlaceholderItem {
  return !(IMPLEMENTED as readonly string[]).includes(item.key);
}

export const routes: RouteObject[] = [
  {
    // First-launch wizard, full screen (no sidebar).
    path: "/welcome",
    lazy: async () => ({
      Component: (await import("@/features/onboarding/OnboardingPage")).OnboardingPage,
    }),
  },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      {
        // Forms, zod and drag and drop are loaded only when the page is opened.
        path: "profile",
        lazy: async () => ({ Component: (await import("@/pages/ProfilePage")).ProfilePage }),
      },
      {
        path: "settings",
        lazy: async () => ({ Component: (await import("@/pages/SettingsPage")).SettingsPage }),
      },
      ...NAV_ITEMS.filter(isPlaceholder).map((item) => ({
        path: item.path.slice(1),
        element: <PlaceholderPage item={item} />,
      })),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
