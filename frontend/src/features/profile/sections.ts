import type { FieldSpec } from "./fields";
import {
  CONTRACT_TYPES,
  EXPERIENCE_TYPES,
  type ItemSection,
  LANGUAGE_LEVELS,
  LEVELS,
  PROJECT_TYPES,
} from "./schema";

/** Form layout of each list section (labels: `profile.fields.<section>.<name>`). */
export const SECTION_FIELDS: Record<ItemSection, readonly FieldSpec[]> = {
  education: [
    { name: "degree", kind: "text" },
    { name: "field", kind: "text" },
    { name: "school", kind: "text" },
    { name: "city", kind: "text" },
    { name: "start", kind: "date" },
    { name: "end", kind: "date" },
    { name: "honors", kind: "text", wide: true },
    { name: "key_courses", kind: "lines", wide: true, hint: "profile.hints.lines" },
    { name: "details", kind: "textarea", wide: true },
  ],
  experiences: [
    { name: "title", kind: "text" },
    { name: "organization", kind: "text" },
    { name: "type", kind: "select", options: EXPERIENCE_TYPES, optionsKey: "experienceType" },
    { name: "city", kind: "text" },
    { name: "start", kind: "date" },
    { name: "end", kind: "date", hint: "profile.hints.ongoing" },
    { name: "context", kind: "textarea", wide: true },
    { name: "achievements", kind: "lines", wide: true, hint: "profile.hints.achievements" },
    { name: "skills", kind: "lines", wide: true, hint: "profile.hints.lines" },
  ],
  projects: [
    { name: "name", kind: "text" },
    { name: "type", kind: "select", options: PROJECT_TYPES, optionsKey: "projectType" },
    { name: "start", kind: "date" },
    { name: "end", kind: "date" },
    { name: "url", kind: "url", wide: true },
    { name: "context", kind: "textarea", wide: true },
    { name: "achievements", kind: "lines", wide: true, hint: "profile.hints.achievements" },
    { name: "skills", kind: "lines", wide: true, hint: "profile.hints.lines" },
  ],
  certifications: [
    { name: "name", kind: "text" },
    { name: "issuer", kind: "text" },
    { name: "date", kind: "date" },
    { name: "url", kind: "url" },
  ],
  awards: [
    { name: "title", kind: "text" },
    { name: "issuer", kind: "text" },
    { name: "date", kind: "date" },
    { name: "description", kind: "textarea", wide: true },
  ],
  volunteering: [
    { name: "role", kind: "text" },
    { name: "organization", kind: "text" },
    { name: "start", kind: "date" },
    { name: "end", kind: "date", hint: "profile.hints.ongoing" },
    { name: "description", kind: "textarea", wide: true },
  ],
  publications: [
    { name: "title", kind: "text", wide: true },
    { name: "venue", kind: "text" },
    { name: "date", kind: "date" },
    { name: "url", kind: "url", wide: true },
  ],
  languages: [
    { name: "name", kind: "text" },
    { name: "level", kind: "select", options: LANGUAGE_LEVELS, optionsKey: "languageLevel" },
    { name: "certificate", kind: "text", wide: true, hint: "profile.hints.certificate" },
  ],
  skills: [
    { name: "category", kind: "text", wide: true },
    { name: "items", kind: "lines", wide: true, hint: "profile.hints.lines" },
  ],
};

/** Fields that build the card title, like the backend merge labels. */
export const SECTION_TITLE_FIELDS: Record<ItemSection, readonly string[]> = {
  education: ["degree", "school"],
  experiences: ["title", "organization"],
  projects: ["name"],
  certifications: ["name", "issuer"],
  awards: ["title", "issuer"],
  volunteering: ["role", "organization"],
  publications: ["title", "venue"],
  languages: ["name", "certificate"],
  skills: ["category"],
};

export const IDENTITY_FIELDS: readonly FieldSpec[] = [
  { name: "first_name", kind: "text" },
  { name: "last_name", kind: "text" },
  { name: "email", kind: "email" },
  { name: "phone", kind: "tel" },
  { name: "city", kind: "text" },
  { name: "mobility", kind: "text" },
  { name: "driving_license", kind: "bool" },
  { name: "linkedin", kind: "url" },
  { name: "github", kind: "url" },
  { name: "portfolio", kind: "url" },
];

export const OBJECTIVE_FIELDS: readonly FieldSpec[] = [
  { name: "contract_type", kind: "select", options: CONTRACT_TYPES, optionsKey: "contractType" },
  { name: "level", kind: "select", options: LEVELS, optionsKey: "level" },
  { name: "domain", kind: "text", wide: true },
  { name: "target_roles", kind: "lines", wide: true, hint: "profile.hints.lines" },
  { name: "availability", kind: "date" },
  { name: "duration_months", kind: "number" },
  { name: "remote_ok", kind: "bool" },
  { name: "zones", kind: "lines", hint: "profile.hints.zones" },
  { name: "salary_min", kind: "number", hint: "profile.hints.salary" },
  { name: "salary_max", kind: "number" },
];

export const PROFILE_TABS = [
  "import",
  "identity",
  "objective",
  "education",
  "experiences",
  "projects",
  "skills",
  "certifications",
  "engagements",
  "backup",
] as const;
export type ProfileTab = (typeof PROFILE_TABS)[number];

/** Which tab shows each top-level key (for error badges). */
export const TAB_OF_KEY: Record<string, ProfileTab> = {
  identity: "identity",
  headline: "identity",
  summary: "identity",
  objective: "objective",
  education: "education",
  experiences: "experiences",
  projects: "projects",
  skills: "skills",
  languages: "skills",
  certifications: "certifications",
  awards: "certifications",
  volunteering: "engagements",
  publications: "engagements",
  interests: "engagements",
  extra_facts: "engagements",
};
