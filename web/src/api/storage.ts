import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { invalidateWithDashboard, keys } from "@/api/keys";
import type { CleanupReport, StorageReport } from "@/api/types";

const CLEANUP_PATH = "/storage/cleanup";

export function useStorage() {
  return useQuery({ queryKey: keys.storage, queryFn: () => api.get<StorageReport>("/storage") });
}

export function useCleanupPreview(enabled: boolean) {
  return useQuery({
    queryKey: keys.cleanupPreview,
    queryFn: () => api.get<CleanupReport>(CLEANUP_PATH),
    enabled,
    staleTime: 0,
    gcTime: 0,
  });
}

export function useCleanUp() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<CleanupReport>(CLEANUP_PATH),
    onSuccess: () => invalidateWithDashboard(client, keys.storage, keys.runs),
  });
}
