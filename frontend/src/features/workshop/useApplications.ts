import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ApplicationDetail, type DocumentsUpdate } from "@/lib/api";

export const APPLICATIONS_KEY = ["applications"] as const;
export const applicationKey = (id: string) => ["application", id] as const;

export function useApplications() {
  return useQuery({ queryKey: APPLICATIONS_KEY, queryFn: api.listApplications });
}

export function useApplication(id: string | null) {
  return useQuery({
    queryKey: applicationKey(id ?? ""),
    queryFn: () => api.getApplication(id ?? ""),
    enabled: Boolean(id),
  });
}

/** Store a fresh detail in the cache and refresh the list (scores, status). */
function useApplyDetail() {
  const queryClient = useQueryClient();
  return (detail: ApplicationDetail) => {
    queryClient.setQueryData(applicationKey(detail.id), detail);
    void queryClient.invalidateQueries({ queryKey: APPLICATIONS_KEY });
  };
}

export function useUpdateDocuments(id: string) {
  const apply = useApplyDetail();
  return useMutation({
    mutationFn: (body: DocumentsUpdate) => api.updateDocuments(id, body),
    onSuccess: apply,
  });
}

export function useMarkSent(id: string) {
  const apply = useApplyDetail();
  return useMutation({ mutationFn: () => api.markSent(id), onSuccess: apply });
}
