import type { LucideIcon } from "lucide-react";
import type * as React from "react";

import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
  headingLevel?: "h1" | "h2";
}

/** Every page has a useful empty state: what it is for, and the main next action. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  badge,
  className,
  headingLevel = "h2",
}: EmptyStateProps) {
  const Heading = headingLevel;
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-lg border border-dashed border-border bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      <span className="flex size-12 items-center justify-center rounded-xl bg-primary-soft text-primary">
        <Icon className="size-6" strokeWidth={1.75} aria-hidden="true" />
      </span>
      <div className="flex max-w-md flex-col items-center gap-2">
        {badge}
        <Heading className="text-lg font-semibold text-ink">{title}</Heading>
        <p className="text-sm leading-relaxed text-muted">{description}</p>
      </div>
      {action}
    </div>
  );
}
