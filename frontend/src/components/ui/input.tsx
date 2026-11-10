import type * as React from "react";

import { cn } from "@/lib/utils";

export const controlClass =
  "w-full rounded-lg border border-border bg-surface-raised px-3 text-sm text-ink shadow-sm transition-colors placeholder:text-muted/70 focus-visible:border-primary focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-ring/30 disabled:cursor-not-allowed disabled:opacity-60 aria-invalid:border-danger";

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return <input data-slot="input" className={cn(controlClass, "h-9", className)} {...props} />;
}
