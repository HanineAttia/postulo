import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useLLMStatus() {
  return useQuery({
    queryKey: ["llm-status"],
    queryFn: api.llmStatus,
    refetchInterval: 60_000,
  });
}
