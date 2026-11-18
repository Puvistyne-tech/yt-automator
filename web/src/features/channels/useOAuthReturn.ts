import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { useSearchParams } from "react-router";
import { useChannels } from "@/api/channels";
import { keys } from "@/api/keys";
import { oauthReturnMessage } from "@/features/channels/credentialForm";
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
    const next = new URLSearchParams(params);
    next.delete("connected");
    next.delete("error");
    next.delete("credential");
    setParams(next, { replace: true });
  }, [params, signature, channels.data, channels.isPending, client, setParams, toast]);
}
