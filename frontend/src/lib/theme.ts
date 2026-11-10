import { readPreference, writePreference } from "./preferences";

export type ThemePreference = "light" | "dark" | "system";

export function readTheme(): ThemePreference {
  const stored = readPreference("theme");
  return stored === "light" || stored === "dark" ? stored : "system";
}

function systemPrefersDark(): boolean {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
    : false;
}

export function applyTheme(preference: ThemePreference): void {
  const dark = preference === "dark" || (preference === "system" && systemPrefersDark());
  document.documentElement.classList.toggle("dark", dark);
}

export function saveTheme(preference: ThemePreference): void {
  writePreference("theme", preference);
  applyTheme(preference);
}

/** Re-apply the "system" theme when the OS setting changes. Returns an unsubscribe function. */
export function watchSystemTheme(getPreference: () => ThemePreference): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const query = window.matchMedia("(prefers-color-scheme: dark)");
  const listener = () => {
    if (getPreference() === "system") applyTheme("system");
  };
  query.addEventListener("change", listener);
  return () => query.removeEventListener("change", listener);
}
