import { useTranslation } from "react-i18next";

import { Skeleton } from "@/components/ui/skeleton";
import { CompletenessCard } from "@/features/profile/CompletenessCard";
import { ProfileEditor } from "@/features/profile/ProfileEditor";
import { useProfile } from "@/features/profile/useProfile";

export function ProfilePage() {
  const { t } = useTranslation();
  const query = useProfile();
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("profile.title")}</h1>
        <p className="text-sm text-muted">{t("profile.subtitle")}</p>
      </div>
      {query.isPending ? (
        <div className="flex flex-col gap-4" aria-busy="true">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : query.isError ? (
        <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">
          {t("errors.server")}
        </p>
      ) : (
        <>
          {query.data.version > 0 ? <CompletenessCard /> : null}
          <ProfileEditor
            stored={query.data}
            onReload={async () => (await query.refetch()).data}
          />
        </>
      )}
    </div>
  );
}
