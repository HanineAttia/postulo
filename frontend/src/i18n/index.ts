import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { readPreference, writePreference } from "@/lib/preferences";

import en from "./en.json";
import fr from "./fr.json";

export const LANGUAGES = ["fr", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

export const resources = { fr: { translation: fr }, en: { translation: en } } as const;

function initialLanguage(): Language {
  const stored = readPreference("language");
  return stored === "en" || stored === "fr" ? stored : "fr";
}

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage(),
  fallbackLng: "fr",
  interpolation: { escapeValue: false }, // React already escapes
  returnNull: false,
});

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
  writePreference("language", lng);
});
document.documentElement.lang = i18n.language;

export default i18n;
