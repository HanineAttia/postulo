import {
  BriefcaseBusiness,
  Building2,
  Compass,
  SquareKanban,
  LayoutDashboard,
  type LucideIcon,
  MessageSquareText,
  PenLine,
  Settings,
  UserRound,
  UsersRound,
} from "lucide-react";

export type NavKey =
  | "dashboard"
  | "offers"
  | "hiddenMarket"
  | "organizations"
  | "workshop"
  | "tracking"
  | "network"
  | "coach"
  | "profile"
  | "settings";

export type NavGroupKey = "find" | "apply" | "prepare" | "mySpace";

export interface NavItem {
  key: NavKey;
  path: string;
  icon: LucideIcon;
  /** Phase of docs/SPEC.md section 14 that delivers the page. */
  phase: number;
}

export interface NavGroup {
  key: NavGroupKey | null;
  items: NavItem[];
}

/** Sidebar structure of docs/SPEC.md section 12.2. */
export const NAVIGATION: NavGroup[] = [
  { key: null, items: [{ key: "dashboard", path: "/", icon: LayoutDashboard, phase: 0 }] },
  {
    key: "find",
    items: [
      { key: "offers", path: "/offers", icon: BriefcaseBusiness, phase: 3 },
      { key: "hiddenMarket", path: "/hidden-market", icon: Compass, phase: 4 },
      { key: "organizations", path: "/organizations", icon: Building2, phase: 3 },
    ],
  },
  {
    key: "apply",
    items: [
      { key: "workshop", path: "/workshop", icon: PenLine, phase: 2 },
      { key: "tracking", path: "/tracking", icon: SquareKanban, phase: 5 },
    ],
  },
  {
    key: "prepare",
    items: [
      { key: "network", path: "/network", icon: UsersRound, phase: 5 },
      { key: "coach", path: "/coach", icon: MessageSquareText, phase: 5 },
    ],
  },
  {
    key: "mySpace",
    items: [
      { key: "profile", path: "/profile", icon: UserRound, phase: 1 },
      { key: "settings", path: "/settings", icon: Settings, phase: 1 },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAVIGATION.flatMap((group) => group.items);
