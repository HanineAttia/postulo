import { Toaster as Sonner } from "sonner";

/** Discreet notifications (SPEC 12.4), styled with the design tokens. */
export function Toaster() {
  return (
    <Sonner
      position="bottom-right"
      closeButton
      toastOptions={{
        classNames: {
          toast:
            "!rounded-lg !border !border-border !bg-surface-raised !text-ink !shadow-md !font-sans",
          description: "!text-muted",
          success: "[&_[data-icon]]:!text-success",
          error: "[&_[data-icon]]:!text-danger",
          actionButton: "!bg-primary !text-primary-foreground",
        },
      }}
    />
  );
}
