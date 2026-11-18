import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { invalidateWithDashboard, keys } from "@/api/keys";
import type {
  Channel,
  ChannelDefaults,
  CredentialInput,
  CredentialPatch,
  CredentialView,
  Playlist,
} from "@/api/types";

const credentialPath = (id: string) => `/credentials/${encodeURIComponent(id)}`;
const channelPath = (id: string) => `/channels/${encodeURIComponent(id)}`;

export function useCredentials() {
  return useQuery({
    queryKey: keys.credentials,
    queryFn: () => api.get<CredentialView[]>("/credentials"),
  });
}

export function useSaveCredential(id: string | undefined) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: CredentialInput | CredentialPatch) =>
      id === undefined
        ? api.post<CredentialView>("/credentials", input)
        : api.patch<CredentialView>(credentialPath(id), input),
    onSuccess: () => invalidateWithDashboard(client, keys.credentials),
  });
}

export function useDeleteCredential() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(credentialPath(id)),
    onSuccess: () => invalidateWithDashboard(client, keys.credentials),
  });
}

export function useChannels() {
  return useQuery({ queryKey: keys.channels, queryFn: () => api.get<Channel[]>("/channels") });
}

export function usePlaylists(channelId: string) {
  return useQuery({
    queryKey: keys.playlists(channelId),
    queryFn: () => api.get<Playlist[]>(`${channelPath(channelId)}/playlists`),
    enabled: channelId !== "",
    staleTime: 60 * 1000,
  });
}

export function useConnectChannel() {
  return useMutation({
    mutationFn: (credentialId: string) =>
      api.post<{ authorization_url: string }>("/channels/connect", {
        credential_id: credentialId,
      }),
  });
}

export function useUpdateChannelDefaults() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, defaults }: { id: string; defaults: ChannelDefaults }) =>
      api.patch<Channel>(channelPath(id), { defaults }),
    onSuccess: () => invalidateWithDashboard(client, keys.channels),
  });
}

export function useDisconnectChannel() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(channelPath(id)),
    onSuccess: () => invalidateWithDashboard(client, keys.channels),
  });
}
