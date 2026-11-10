import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink, useMatch } from "react-router";

import { LogoMark } from "@/components/Logo";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import { NAVIGATION, type NavItem } from "../navigation";

function SidebarLink({ item, label, collapsed }: { item: NavItem; label: string; collapsed: boolean }) {
  // A string className (not NavLink's function form): the tooltip trigger merges props
  // through Radix Slot, which would stringify a function.
  const isActive = useMatch({ path: item.path, end: item.path === "/" }) !== null;
  const Icon = item.icon;
  return (
    <Tooltip content={label} side="right" enabled={collapsed}>
      <NavLink
        to={item.path}
        end={item.path === "/"}
        aria-label={collapsed ? label : undefined}
        className={cn(
          "flex h-9 items-center gap-3 rounded-lg px-3 text-sm font-medium text-muted transition-colors hover:bg-surface-raised hover:text-ink",
          collapsed && "justify-center px-0",
          isActive &&
            "bg-surface-raised text-primary shadow-sm ring-1 ring-border hover:text-primary",
        )}
      >
        <Icon className="size-[18px] shrink-0" strokeWidth={1.75} aria-hidden="true" />
        {!collapsed && <span className="truncate">{label}</span>}
      </NavLink>
    </Tooltip>
  );
}

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { t } = useTranslation();
  const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;
  const toggleLabel = collapsed ? t("nav.expand") : t("nav.collapse");

  return (
    <aside
      data-collapsed={collapsed}
      className={cn(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <div className={cn("flex h-14 items-center gap-2.5 px-4", collapsed && "justify-center px-0")}>
        <LogoMark className="size-7" />
        {!collapsed && (
          <span className="text-[15px] font-semibold tracking-tight text-ink">{t("app.name")}</span>
        )}
      </div>

      <nav aria-label={t("nav.mainLabel")} className="flex-1 overflow-y-auto px-2 py-2">
        {NAVIGATION.map((group, index) => {
          const headingId = group.key ? `nav-group-${group.key}` : undefined;
          return (
            <div key={group.key ?? `group-${index}`} className={cn(index > 0 && "mt-5")}>
              {group.key &&
                (collapsed ? (
                  <div className="mx-3 mb-2 border-t border-border" aria-hidden="true" />
                ) : (
                  <h2
                    id={headingId}
                    className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted"
                  >
                    {t(`nav.groups.${group.key}`)}
                  </h2>
                ))}
              <ul aria-labelledby={collapsed ? undefined : headingId} className="flex flex-col gap-0.5">
                {group.items.map((item) => (
                  <li key={item.key}>
                    <SidebarLink item={item} label={t(`nav.${item.key}`)} collapsed={collapsed} />
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      <div className={cn("border-t border-border p-2", collapsed && "flex justify-center")}>
        <Tooltip content={toggleLabel} side="right" enabled={collapsed}>
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={!collapsed}
            aria-label={toggleLabel}
            className={cn(
              "flex h-9 items-center gap-3 rounded-lg px-3 text-sm text-muted transition-colors hover:bg-surface-raised hover:text-ink",
              collapsed ? "w-9 justify-center px-0" : "w-full",
            )}
          >
            <ToggleIcon className="size-[18px]" strokeWidth={1.75} aria-hidden="true" />
            {!collapsed && <span>{t("nav.collapse")}</span>}
          </button>
        </Tooltip>
      </div>
    </aside>
  );
}
