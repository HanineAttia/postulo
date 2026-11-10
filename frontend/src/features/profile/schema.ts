/**
 * Career library schema, mirrored from backend/postulo/services/profile/schema.py.
 * The backend stays the source of truth (it normalizes dates, links and lines);
 * this schema validates forms before saving. Messages are i18n keys.
 */
import { z } from "zod";

export const CONTRACT_TYPES = [
  "internship",
  "apprenticeship",
  "fixed_term",
  "permanent",
  "freelance",
] as const;
export const LEVELS = ["student", "recent_graduate", "junior", "experienced", "senior"] as const;
export const EXPERIENCE_TYPES = [
  "internship",
  "apprenticeship",
  "permanent",
  "fixed_term",
  "freelance",
  "student_job",
  "mission",
  "research",
  "volunteering",
] as const;
export const PROJECT_TYPES = [
  "academic",
  "personal",
  "professional",
  "hackathon",
  "research",
  "open_source",
] as const;
export const LANGUAGE_LEVELS = ["native", "bilingual", "c1_c2", "b2", "b1", "a1_a2"] as const;

const YEAR_MONTH_RE = /^\d{4}(-(0[1-9]|1[0-2]))?$/;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE_RE = /^\+?[\d\s.\-()/]+$/;
const URL_RE = /^([a-zA-Z][a-zA-Z0-9+.-]*:\/\/\S+|[^\s/]+\.[^\s]+)$/;

const text = z.string();
const lines = z.array(z.string());
const yearMonth = z.string().regex(YEAR_MONTH_RE, "validation.date").nullable();
const url = z.string().regex(URL_RE, "validation.url").nullable();
const email = z.string().regex(EMAIL_RE, "validation.email").nullable();
const phone = z
  .string()
  .refine((value) => {
    const digits = value.replace(/\D/g, "").length;
    return PHONE_RE.test(value) && digits >= 8 && digits <= 15;
  }, "validation.phone")
  .nullable();
const id = z.string();

export const linkSchema = z.object({ id, label: text, url });

export const identitySchema = z.object({
  first_name: text,
  last_name: text,
  email,
  phone,
  city: text,
  mobility: text,
  driving_license: z.boolean().nullable(),
  linkedin: url,
  github: url,
  portfolio: url,
  links: z.array(linkSchema),
});

export const objectiveSchema = z
  .object({
    contract_type: z.enum(CONTRACT_TYPES).nullable(),
    level: z.enum(LEVELS).nullable(),
    domain: text,
    target_roles: lines,
    availability: yearMonth,
    duration_months: z.number().int("validation.integer").min(1, "validation.duration").max(60, "validation.duration").nullable(),
    remote_ok: z.boolean().nullable(),
    zones: lines,
    salary_min: z.number().int("validation.integer").min(0, "validation.positive").nullable(),
    salary_max: z.number().int("validation.integer").min(0, "validation.positive").nullable(),
  })
  .refine(
    (o) => o.salary_min === null || o.salary_max === null || o.salary_min <= o.salary_max,
    { message: "validation.salaryRange", path: ["salary_max"] },
  );

/** End must not be before start (both "AAAA" or "AAAA-MM", compared as strings). */
function datesInOrder<T extends { start: string | null; end: string | null }>(item: T) {
  return !item.start || !item.end || item.end.slice(0, item.start.length) >= item.start.slice(0, item.end.length);
}
const dateOrder = { message: "validation.dateOrder", path: ["end"] };

export const educationSchema = z
  .object({
    id,
    degree: text,
    field: text,
    school: text,
    city: text,
    start: yearMonth,
    end: yearMonth,
    honors: text,
    key_courses: lines,
    details: text,
  })
  .refine(datesInOrder, dateOrder);

export const experienceSchema = z
  .object({
    id,
    title: text,
    organization: text,
    city: text,
    type: z.enum(EXPERIENCE_TYPES).nullable(),
    start: yearMonth,
    end: yearMonth,
    context: text,
    achievements: lines,
    skills: lines,
  })
  .refine(datesInOrder, dateOrder);

export const projectSchema = z
  .object({
    id,
    name: text,
    type: z.enum(PROJECT_TYPES).nullable(),
    start: yearMonth,
    end: yearMonth,
    context: text,
    achievements: lines,
    skills: lines,
    url,
  })
  .refine(datesInOrder, dateOrder);

export const certificationSchema = z.object({ id, name: text, issuer: text, date: yearMonth, url });
export const awardSchema = z.object({
  id,
  title: text,
  issuer: text,
  date: yearMonth,
  description: text,
});
export const volunteeringSchema = z
  .object({
    id,
    role: text,
    organization: text,
    start: yearMonth,
    end: yearMonth,
    description: text,
  })
  .refine(datesInOrder, dateOrder);
export const publicationSchema = z.object({ id, title: text, venue: text, date: yearMonth, url });
export const languageSchema = z.object({
  id,
  name: text,
  level: z.enum(LANGUAGE_LEVELS).nullable(),
  certificate: text,
});
export const skillGroupSchema = z.object({ id, category: text, items: lines });

export const careerProfileSchema = z.object({
  identity: identitySchema,
  headline: text,
  summary: text,
  objective: objectiveSchema,
  education: z.array(educationSchema),
  experiences: z.array(experienceSchema),
  projects: z.array(projectSchema),
  certifications: z.array(certificationSchema),
  awards: z.array(awardSchema),
  volunteering: z.array(volunteeringSchema),
  publications: z.array(publicationSchema),
  languages: z.array(languageSchema),
  skills: z.array(skillGroupSchema),
  interests: lines,
  extra_facts: lines,
});

export type CareerProfile = z.infer<typeof careerProfileSchema>;
export type Identity = z.infer<typeof identitySchema>;
export type Objective = z.infer<typeof objectiveSchema>;
export type Experience = z.infer<typeof experienceSchema>;

export const ITEM_SECTIONS = [
  "education",
  "experiences",
  "projects",
  "certifications",
  "awards",
  "volunteering",
  "publications",
  "languages",
  "skills",
] as const;
export type ItemSection = (typeof ITEM_SECTIONS)[number];
export type SectionItem<S extends ItemSection> = CareerProfile[S][number];

export function newId(): string {
  return crypto.randomUUID().replace(/-/g, "").slice(0, 12);
}

const EMPTY_ITEMS: { [S in ItemSection]: () => SectionItem<S> } = {
  education: () => ({
    id: newId(),
    degree: "",
    field: "",
    school: "",
    city: "",
    start: null,
    end: null,
    honors: "",
    key_courses: [],
    details: "",
  }),
  experiences: () => ({
    id: newId(),
    title: "",
    organization: "",
    city: "",
    type: null,
    start: null,
    end: null,
    context: "",
    achievements: [],
    skills: [],
  }),
  projects: () => ({
    id: newId(),
    name: "",
    type: null,
    start: null,
    end: null,
    context: "",
    achievements: [],
    skills: [],
    url: null,
  }),
  certifications: () => ({ id: newId(), name: "", issuer: "", date: null, url: null }),
  awards: () => ({ id: newId(), title: "", issuer: "", date: null, description: "" }),
  volunteering: () => ({
    id: newId(),
    role: "",
    organization: "",
    start: null,
    end: null,
    description: "",
  }),
  publications: () => ({ id: newId(), title: "", venue: "", date: null, url: null }),
  languages: () => ({ id: newId(), name: "", level: null, certificate: "" }),
  skills: () => ({ id: newId(), category: "", items: [] }),
};

export function emptyItem<S extends ItemSection>(section: S): SectionItem<S> {
  return EMPTY_ITEMS[section]();
}

export function emptyProfile(): CareerProfile {
  return {
    identity: {
      first_name: "",
      last_name: "",
      email: null,
      phone: null,
      city: "",
      mobility: "",
      driving_license: null,
      linkedin: null,
      github: null,
      portfolio: null,
      links: [],
    },
    headline: "",
    summary: "",
    objective: {
      contract_type: null,
      level: null,
      domain: "",
      target_roles: [],
      availability: null,
      duration_months: null,
      remote_ok: null,
      zones: [],
      salary_min: null,
      salary_max: null,
    },
    education: [],
    experiences: [],
    projects: [],
    certifications: [],
    awards: [],
    volunteering: [],
    publications: [],
    languages: [],
    skills: [],
    interests: [],
    extra_facts: [],
  };
}

/** Drop empty lines (kept while typing so Enter works) before saving. */
export function cleanLines(profile: CareerProfile): CareerProfile {
  return JSON.parse(
    JSON.stringify(profile, (_key, value: unknown) =>
      Array.isArray(value) && value.every((v) => typeof v === "string")
        ? (value as string[]).map((v) => v.trim()).filter(Boolean)
        : value,
    ),
  ) as CareerProfile;
}
