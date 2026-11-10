import { DropdownMenu } from "radix-ui";
import { Check, Cpu, FlaskConical, Languages, Monitor, Moon, Search, Sun } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip } from "@/components/ui/tooltip";
import { useLLMStatus } from "@/features/llm/useLLMStatus";
import { LANGUAGES, type Language } from "@/i18n";
import { readTheme, saveTheme, type ThemePreference } from "@/lib/theme";

const THEME_ICONS: Record<ThemePreference, typeof Sun> = { light: Sun, dark: Moon, system: Monitor };

export function Header() {
  const { t } = useTranslation();
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/90 px-6 backdrop-blur">
      <Tooltip content={t("header.searchSoon")}>
        <button
          type="button"
          aria-disabled="true"
          aria-keyshortcuts="Control+K"
          className="flex h-9 w-72 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm text-muted aria-disabled:cursor-not-allowed"
        >
          <Search className="size-4" aria-hidden="true" />
          <span className="flex-1 text-left">{t("header.search")}</span>
          <kbd className="rounded border border-border bg-surface-raised px-1.5 text-[11px] font-medium">
            Ctrl K
          </kbd>
        </button>
      </Tooltip>

      <div className="ml-auto flex items-center gap-2">
        <AIIndicator />
        <ThemeMenu />
        <LanguageMenu />
      </div>
    </header>
  );
}

function AIIndicator() {
  const { t } = useTranslation();
  const { data, isPending, isError } = useLLMStatus();

  if (isPending) return <Skeleton className="h-6 w-52" />;
  if (isError || !data) {
    return <Badge variant="danger">{t("errors.server")}</Badge>;
  }
  return (
    <div className="flex items-center gap-2">
      <span className="tabular text-xs text-muted" data-testid="ai-calls">
        {t("header.aiCalls", { count: data.calls_today })}
      </span>
      {data.demo_mode ? (
        <Tooltip content={t("header.demoModeHint")}>
          <Badge variant="primary" tabIndex={0}>
            <FlaskConical aria-hidden="true" />
            {t("header.demoMode")}
          </Badge>
        </Tooltip>
      ) : (
        <Tooltip content={data.available ? data.reason : t("header.providerUnavailable")}>
          <Badge variant={data.available ? "neutral" : "warning"} tabIndex={0}>
            <Cpu aria-hidden="true" />
            {t(`providers.${data.provider}`)}
          </Badge>
        </Tooltip>
      )}
    </div>
  );
}

const menuContentClass =
  "z-50 min-w-40 rounded-lg border border-border bg-surface-raised p-1 shadow-md";
const menuItemClass =
  "flex cursor-default select-none items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink outline-none data-[highlighted]:bg-surface [&_svg]:size-4";

function ThemeMenu() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<ThemePreference>(readTheme);
  const Icon = THEME_ICONS[theme];
  const choose = (value: ThemePreference) => {
    setTheme(value);
    saveTheme(value);
  };
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={t("header.theme.label")}>
          <Icon aria-hidden="true" />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className={menuContentClass}>
          <DropdownMenu.RadioGroup
            value={theme}
            onValueChange={(value) => choose(value as ThemePreference)}
          >
            {(["light", "dark", "system"] as const).map((value) => {
              const ItemIcon = THEME_ICONS[value];
              return (
                <DropdownMenu.RadioItem key={value} value={value} className={menuItemClass}>
                  <ItemIcon aria-hidden="true" />
                  <span className="flex-1">{t(`header.theme.${value}`)}</span>
                  <DropdownMenu.ItemIndicator>
                    <Check aria-hidden="true" />
                  </DropdownMenu.ItemIndicator>
                </DropdownMenu.RadioItem>
              );
            })}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function LanguageMenu() {
  const { t, i18n } = useTranslation();
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label={t("header.language")}>
          <Languages aria-hidden="true" />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className={menuContentClass}>
          <DropdownMenu.RadioGroup
            value={i18n.language}
            onValueChange={(value) => void i18n.changeLanguage(value as Language)}
          >
            {LANGUAGES.map((lng) => (
              <DropdownMenu.RadioItem key={lng} value={lng} lang={lng} className={menuItemClass}>
                <span className="flex-1">{t(`header.languages.${lng}`)}</span>
                <DropdownMenu.ItemIndicator>
                  <Check aria-hidden="true" />
                </DropdownMenu.ItemIndicator>
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
