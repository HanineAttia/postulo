import type * as React from "react";
import { Controller, get, type Path, useFormContext, useFormState } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { describedBy, Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { useDynamicT } from "@/lib/i18nKey";

import type { CareerProfile } from "./schema";

export type ProfilePath = Path<CareerProfile>;

export type FieldKind = "text" | "textarea" | "lines" | "date" | "url" | "email" | "tel" | "number" | "select" | "bool";

export interface FieldSpec {
  /** Field name inside the item / object (e.g. "title"). */
  name: string;
  kind: FieldKind;
  /** Enum values for `select`, translated with `enums.<optionsKey>.<value>`. */
  options?: readonly string[];
  optionsKey?: string;
  /** Takes the full row width. */
  wide?: boolean;
  /** i18n key of a hint shown under the field. */
  hint?: string;
}

const nullIfEmpty = (value: unknown) =>
  typeof value === "string" && value.trim() === "" ? null : value;

function fieldId(path: string): string {
  return `field-${path.replace(/\./g, "-")}`;
}

interface BoundFieldProps {
  path: string;
  spec: FieldSpec;
  /** i18n key prefix for the label: `<labelPrefix>.<name>`. */
  labelPrefix: string;
}

/** One form field bound to react-hook-form, with label, hint and translated error. */
export function BoundField({ path, spec, labelPrefix }: BoundFieldProps) {
  const { t } = useTranslation();
  const td = useDynamicT();
  const { register, control } = useFormContext<CareerProfile>();
  const { errors } = useFormState({ control, name: path as ProfilePath });
  const error = (get(errors, path) as { message?: string } | undefined)?.message;
  const id = fieldId(path);
  const hint = spec.hint ? td(spec.hint) : undefined;
  const common = {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": describedBy(id, error, hint),
  };
  const name = path as ProfilePath;
  let control_: React.ReactNode;

  switch (spec.kind) {
    case "textarea":
      control_ = <Textarea {...common} rows={3} {...register(name)} />;
      break;
    case "lines":
      control_ = (
        <Controller
          control={control}
          name={name}
          render={({ field }) => (
            <Textarea
              {...common}
              rows={4}
              name={field.name}
              ref={field.ref}
              onBlur={field.onBlur}
              value={Array.isArray(field.value) ? (field.value as string[]).join("\n") : ""}
              onChange={(event) => field.onChange(event.target.value.split("\n"))}
            />
          )}
        />
      );
      break;
    case "date":
      control_ = (
        <Input
          {...common}
          placeholder={t("profile.datePlaceholder")}
          inputMode="numeric"
          autoComplete="off"
          {...register(name, { setValueAs: nullIfEmpty })}
        />
      );
      break;
    case "number":
      control_ = (
        <Input
          {...common}
          type="number"
          inputMode="numeric"
          {...register(name, {
            setValueAs: (value: unknown) =>
              value === "" || value === null || value === undefined ? null : Number(value),
          })}
        />
      );
      break;
    case "select":
      control_ = (
        <NativeSelect {...common} {...register(name, { setValueAs: nullIfEmpty })}>
          <option value="">{t("profile.notSpecified")}</option>
          {(spec.options ?? []).map((option) => (
            <option key={option} value={option}>
              {td(`enums.${spec.optionsKey ?? spec.name}.${option}`)}
            </option>
          ))}
        </NativeSelect>
      );
      break;
    case "bool":
      control_ = (
        <Controller
          control={control}
          name={name}
          render={({ field }) => (
            <NativeSelect
              {...common}
              name={field.name}
              ref={field.ref}
              onBlur={field.onBlur}
              value={field.value === true ? "yes" : field.value === false ? "no" : ""}
              onChange={(event) =>
                field.onChange(
                  event.target.value === "yes" ? true : event.target.value === "no" ? false : null,
                )
              }
            >
              <option value="">{t("profile.notSpecified")}</option>
              <option value="yes">{t("profile.yes")}</option>
              <option value="no">{t("profile.no")}</option>
            </NativeSelect>
          )}
        />
      );
      break;
    default:
      control_ = (
        <Input
          {...common}
          type={spec.kind === "email" ? "email" : spec.kind === "tel" ? "tel" : "text"}
          autoComplete="off"
          {...register(name, {
            setValueAs: ["url", "email", "tel"].includes(spec.kind) ? nullIfEmpty : undefined,
          })}
        />
      );
  }

  return (
    <Field
      id={id}
      label={td(`${labelPrefix}.${spec.name}`)}
      hint={hint}
      error={error}
      className={spec.wide ? "sm:col-span-2" : undefined}
    >
      {control_}
    </Field>
  );
}

/** A responsive two-column grid of bound fields. */
export function FieldGrid({
  prefix,
  specs,
  labelPrefix,
}: {
  prefix: string;
  specs: readonly FieldSpec[];
  labelPrefix: string;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {specs.map((spec) => (
        <BoundField
          key={spec.name}
          path={prefix ? `${prefix}.${spec.name}` : spec.name}
          spec={spec}
          labelPrefix={labelPrefix}
        />
      ))}
    </div>
  );
}
