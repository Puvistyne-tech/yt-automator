import { useConnectChannel } from "@/api/channels";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { useExternalNavigate } from "@/shared/hooks/externalNavigation";

export interface StartConnect {
  start: (credentialId: string) => void;
  pending: boolean;
}

export function useStartConnect(): StartConnect {
  const connect = useConnectChannel();
  const navigateExternal = useExternalNavigate();
  const notifier = useMutationNotifier();
  const start = (credentialId: string) =>
    connect.mutate(credentialId, {
      onSuccess: ({ authorization_url }) => navigateExternal(authorization_url),
      onError: notifier.fail,
    });
  return { start, pending: connect.isPending };
}
