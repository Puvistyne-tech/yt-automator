import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { keys } from "@/api/keys";
import type { Dashboard, PipelineDescriptor } from "@/api/types";

export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: () => api.get<Dashboard>("/dashboard") });
}

export function usePipelines() {
  return useQuery({
    queryKey: keys.pipelines,
    queryFn: () => api.get<PipelineDescriptor[]>("/pipelines"),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePipeline(typeId: string | undefined) {
  return useQuery({
    queryKey: keys.pipeline(typeId ?? ""),
    queryFn: () => api.get<PipelineDescriptor>(`/pipelines/${encodeURIComponent(typeId ?? "")}`),
    enabled: typeId !== undefined && typeId !== "",
    staleTime: 5 * 60 * 1000,
  });
}
