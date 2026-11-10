import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Settings, type SettingsRead } from "@/lib/api";

export const SETTINGS_KEY = ["settings"] as const;

export function useSettings() {
  return useQuery({ queryKey: SETTINGS_KEY, queryFn: api.getSettings });
}

export function toSettings(read: SettingsRead): Settings {
  return {
    ai: read.ai,
    ui: read.ui,
    documents: read.documents,
    onboarding_completed: read.onboarding_completed,
  };
}

/** Save the full settings object, then refresh the header status. */
export function useSaveSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.saveSettings,
    onSuccess: (saved) => {
      queryClient.setQueryData(SETTINGS_KEY, saved);
      void queryClient.invalidateQueries({ queryKey: ["llm-status"] });
    },
  });
}
