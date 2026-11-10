import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ImportMode, type StoredProfile } from "@/lib/api";

import type { CareerProfile } from "./schema";

export const PROFILE_KEY = ["profile"] as const;
export const COMPLETENESS_KEY = ["profile-completeness"] as const;

export function useProfile() {
  return useQuery({ queryKey: PROFILE_KEY, queryFn: api.getProfile });
}

export function useCompleteness() {
  return useQuery({ queryKey: COMPLETENESS_KEY, queryFn: api.completeness });
}

/** Store a saved profile in the cache and refresh what depends on it. */
export function useProfileSaved() {
  const queryClient = useQueryClient();
  return (stored: StoredProfile) => {
    queryClient.setQueryData(PROFILE_KEY, stored);
    void queryClient.invalidateQueries({ queryKey: COMPLETENESS_KEY });
  };
}

export function useSaveProfile() {
  const onSaved = useProfileSaved();
  return useMutation({
    mutationFn: ({ version, profile }: { version: number; profile: CareerProfile }) =>
      api.saveProfile(version, profile),
    onSuccess: onSaved,
  });
}

export function useApplyImport() {
  const onSaved = useProfileSaved();
  return useMutation({
    mutationFn: ({
      mode,
      incoming,
      version,
    }: {
      mode: ImportMode;
      incoming: CareerProfile;
      version: number;
    }) => api.applyImport(mode, incoming, version),
    onSuccess: onSaved,
  });
}

export function useLoadSample() {
  const onSaved = useProfileSaved();
  return useMutation({ mutationFn: (force: boolean) => api.loadSample(force), onSuccess: onSaved });
}
