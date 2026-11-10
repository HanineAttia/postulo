import type * as React from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

import { Label } from "./label";

interface FieldProps {
  id: string;
  label: string;
  hint?: string;
  /** i18n key of the validation message. */
  error?: string;
  className?: string;
  children: React.ReactNode;
}

/** Label + control + hint + error, linked with aria-describedby by the caller via ids. */
export function Field({ id, label, hint, error, className, children }: FieldProps) {
  const { t } = useTranslation();
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && !error ? (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs text-danger">
          {/* Messages come from the zod schema as i18n keys. */}
          {t(error as "validation.date", { defaultValue: t("validation.invalid") })}
        </p>
      ) : null}
    </div>
  );
}

export function describedBy(id: string, error?: string, hint?: string): string | undefined {
  if (error) return `${id}-error`;
  if (hint) return `${id}-hint`;
  return undefined;
}
