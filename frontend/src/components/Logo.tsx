import { cn } from "@/lib/utils";

/** Monogram: white "P" in a navy rounded square with a light-blue dot (SPEC 12.1). */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className={cn("size-8 shrink-0", className)}>
      <rect width="64" height="64" rx="15" fill="#1D4E89" />
      <path
        d="M23 47V17h10.5a9.5 9.5 0 0 1 0 19H23"
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="44.5" cy="45" r="4.5" fill="#7FB3F0" />
    </svg>
  );
}
