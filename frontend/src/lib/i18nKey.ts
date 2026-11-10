import { useTranslation } from "react-i18next";

export type DynamicT = (key: string, options?: Record<string, unknown>) => string;

/**
 * Translate keys built at runtime (field labels, enum values, advice), which the typed
 * i18n resources cannot check. Missing keys fall back to French, then to the key.
 */
export function useDynamicT(): DynamicT {
  const { t } = useTranslation();
  return t as unknown as DynamicT;
}
