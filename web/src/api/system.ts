import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { keys } from "@/api/keys";
import type {
  AppSettings,
  AppSettingsInput,
  ProviderConfig,
  ProvidersResponse,
  SecretInfo,
} from "@/api/types";

const secretPath = (name: string) => `/secrets/${encodeURIComponent(name)}`;

export function useProviders() {
  return useQuery({
    queryKey: keys.providers,
    queryFn: () => api.get<ProvidersResponse>("/providers"),
  });
}

export function useSaveProviders() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (config: ProviderConfig[]) => api.put<ProviderConfig[]>("/providers", config),
    onSuccess: (config) => {
      client.setQueryData<ProvidersResponse>(keys.providers, (current) =>
        current === undefined ? current : { ...current, config },
      );
      return client.invalidateQueries({ queryKey: keys.providers });
    },
  });
}

export function useSecrets() {
  return useQuery({ queryKey: keys.secrets, queryFn: () => api.get<SecretInfo[]>("/secrets") });
}

export function useSetSecret() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ name, value }: { name: string; value: string }) =>
      api.put<null>(secretPath(name), { value }),
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: keys.secrets }),
        client.invalidateQueries({ queryKey: keys.providers }),
      ]),
  });
}

export function useClearSecret() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.delete(secretPath(name)),
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: keys.secrets }),
        client.invalidateQueries({ queryKey: keys.providers }),
      ]),
  });
}

export function useAppSettings() {
  return useQuery({ queryKey: keys.settings, queryFn: () => api.get<AppSettings>("/settings") });
}

export function useSaveAppSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: AppSettingsInput) => api.put<AppSettings>("/settings", input),
    onSuccess: (saved) => client.setQueryData(keys.settings, saved),
  });
}
