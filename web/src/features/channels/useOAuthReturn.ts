import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import { useChannels } from "@/api/channels";
import { keys } from "@/api/keys";
import { oauthReturnMessage, withoutOAuthParams } from "@/features/channels/oauthReturn";
import { useToast } from "@/shared/ui";

export function useOAuthReturn() {
  const [params, setParams] = useSearchParams();
  const channels = useChannels();
  const client = useQueryClient();
  const toast = useToast();
  const handled = useRef<string | null>(null);
  const signature = params.toString();

  useEffect(() => {
    const result = oauthReturnMessage(
      params,
      (id) => channels.data?.find((c) => c.id === id)?.title,
    );
    const waitingForTitle = params.has("connected") && channels.isPending;
    if (result === null || waitingForTitle || handled.current === signature) {
      return;
    }
    handled.current = signature;
    toast[result.tone](result.message);
    void client.invalidateQueries({ queryKey: keys.channels });
    setParams(withoutOAuthParams(params), { replace: true });
  }, [params, signature, channels.data, channels.isPending, client, setParams, toast]);
}
