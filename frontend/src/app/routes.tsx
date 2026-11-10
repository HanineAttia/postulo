import type { RouteObject } from "react-router";

import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PlaceholderPage } from "@/pages/PlaceholderPage";

import { AppLayout } from "./layout/AppLayout";
import { NAV_ITEMS, type NavItem } from "./navigation";

type PlaceholderItem = NavItem & { key: Exclude<NavItem["key"], "dashboard"> };

function isPlaceholder(item: NavItem): item is PlaceholderItem {
  return item.key !== "dashboard";
}

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      ...NAV_ITEMS.filter(isPlaceholder).map((item) => ({
        path: item.path.slice(1),
        element: <PlaceholderPage item={item} />,
      })),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
