import { type QueryClient, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiUrl, requestText } from "@/api/client";
import { keys } from "@/api/keys";
import type { LogLine, Run, RunFilters } from "@/api/types";

const path = (id: string) => `/runs/${encodeURIComponent(id)}`;

export function artifactUrl(runId: string, artifactId: string): string {
  return apiUrl(`${path(runId)}/artifacts/${encodeURIComponent(artifactId)}`);
}

export function useRuns(filters: RunFilters) {
  return useQuery({
    queryKey: keys.runList(filters),
    queryFn: () =>
      api.get<Run[]>("/runs", {
        automation_id: filters.automation_id,
        status: filters.status,
        limit: filters.limit,
      }),
  });
}

export function useRun(id: string | undefined) {
  return useQuery({
    queryKey: keys.run(id ?? ""),
    queryFn: () => api.get<Run>(path(id ?? "")),
    enabled: id !== undefined,
  });
}

export function useRunLogs(id: string) {
  return useQuery<LogLine[]>({
    queryKey: keys.runLogs(id),
    queryFn: () => [],
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: Number.POSITIVE_INFINITY,
  });
}

export function useArtifactText(runId: string, artifactId: string) {
  return useQuery({
    queryKey: keys.artifactText(runId, artifactId),
    queryFn: () => requestText(`${path(runId)}/artifacts/${encodeURIComponent(artifactId)}`),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

function storeRun(client: QueryClient, run: Run) {
  client.setQueryData(keys.run(run.id), run);
  return Promise.all([
    client.invalidateQueries({ queryKey: ["runs", "list"] }),
    client.invalidateQueries({ queryKey: keys.dashboard }),
    client.invalidateQueries({ queryKey: keys.automations }),
  ]);
}

function useRunAction<V>(call: (id: string, vars: V) => Promise<Run>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, vars }: { id: string; vars: V }) => call(id, vars),
    onSuccess: (run) => storeRun(client, run),
  });
}

export const useRetryRun = () =>
  useRunAction<{ from_stage?: string }>((id, vars) => api.post<Run>(`${path(id)}/retry`, vars));

export const useCancelRun = () =>
  useRunAction<undefined>((id) => api.post<Run>(`${path(id)}/cancel`));

export const useReviewRun = () =>
  useRunAction<{ decision: "approved" | "rejected"; notes?: string }>((id, vars) =>
    api.post<Run>(`${path(id)}/review`, vars),
  );

export const usePublishRun = () =>
  useRunAction<undefined>((id) => api.post<Run>(`${path(id)}/publish`));

export function useDeleteRun() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(path(id)),
    onSuccess: (_result, id) => {
      client.removeQueries({ queryKey: keys.run(id) });
      return Promise.all([
        client.invalidateQueries({ queryKey: ["runs", "list"] }),
        client.invalidateQueries({ queryKey: keys.dashboard }),
      ]);
    },
  });
}
