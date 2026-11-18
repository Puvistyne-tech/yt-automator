import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { invalidateWithDashboard, keys } from "@/api/keys";
import type { Automation, AutomationInput, Run } from "@/api/types";

const path = (id: string) => `/automations/${encodeURIComponent(id)}`;

export function useAutomations() {
  return useQuery({
    queryKey: keys.automations,
    queryFn: () => api.get<Automation[]>("/automations"),
  });
}

export function useAutomation(id: string | undefined) {
  return useQuery({
    queryKey: keys.automation(id ?? ""),
    queryFn: () => api.get<Automation>(path(id ?? "")),
    enabled: id !== undefined,
  });
}

export function useSaveAutomation(id: string | undefined) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: AutomationInput) =>
      id === undefined
        ? api.post<Automation>("/automations", input)
        : api.put<Automation>(path(id), input),
    onSuccess: (saved) => {
      client.setQueryData(keys.automation(saved.id), saved);
      return invalidateWithDashboard(client, keys.automations);
    },
  });
}

export function useToggleAutomation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.patch<Automation>(path(id), { enabled }),
    onMutate: async ({ id, enabled }) => {
      await client.cancelQueries({ queryKey: keys.automations });
      const previous = client.getQueryData<Automation[]>(keys.automations);
      client.setQueryData<Automation[]>(keys.automations, (list) =>
        list?.map((item) => (item.id === id ? { ...item, enabled } : item)),
      );
      return { previous };
    },
    onError: (_error, _vars, context) => {
      client.setQueryData(keys.automations, context?.previous);
    },
    onSettled: () => invalidateWithDashboard(client, keys.automations),
  });
}

export function useDeleteAutomation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(path(id)),
    onSuccess: () => invalidateWithDashboard(client, keys.automations),
  });
}

export function useDuplicateAutomation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Automation>(`${path(id)}/duplicate`),
    onSuccess: () => invalidateWithDashboard(client, keys.automations),
  });
}

export function useRunAutomation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Run>(`${path(id)}/runs`),
    onSuccess: () => invalidateWithDashboard(client, keys.automations, keys.runs),
  });
}
