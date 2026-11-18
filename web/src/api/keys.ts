import type { QueryClient } from "@tanstack/react-query";
import type { RunFilters } from "@/api/types";

export const keys = {
  dashboard: ["dashboard"] as const,
  pipelines: ["pipelines"] as const,
  pipeline: (typeId: string) => ["pipelines", typeId] as const,
  credentials: ["credentials"] as const,
  channels: ["channels"] as const,
  playlists: (channelId: string) => ["channels", channelId, "playlists"] as const,
  automations: ["automations"] as const,
  automation: (id: string) => ["automations", id] as const,
  runs: ["runs"] as const,
  runLists: ["runs", "list"] as const,
  runList: (filters: RunFilters) => ["runs", "list", filters] as const,
  run: (id: string) => ["runs", "detail", id] as const,
  artifactText: (runId: string, artifactId: string) =>
    ["artifact-text", runId, artifactId] as const,
  providers: ["providers"] as const,
  secrets: ["secrets"] as const,
  settings: ["settings"] as const,
  storage: ["storage"] as const,
  cleanupPreview: ["storage", "cleanup"] as const,
};

export function invalidateWithDashboard(
  client: QueryClient,
  ...queryKeys: (readonly string[])[]
): Promise<unknown> {
  return Promise.all(
    [...queryKeys, keys.dashboard].map((queryKey) => client.invalidateQueries({ queryKey })),
  );
}
