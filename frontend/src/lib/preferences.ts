/**
 * Per-browser UI conveniences (theme, language, sidebar state).
 * Storage can be unavailable (private mode, blocked site data): never throw.
 */
const PREFIX = "postulo.";

export function readPreference(key: string): string | null {
  try {
    return window.localStorage.getItem(PREFIX + key);
  } catch {
    return null;
  }
}

export function writePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(PREFIX + key, value);
  } catch {
    // ignore: preferences are optional
  }
}
