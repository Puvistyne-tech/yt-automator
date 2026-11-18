import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiUrl } from "@/api/client";
import { invalidateWithDashboard, keys } from "@/api/keys";
import { applyRunEvent, parseRunEvent, reconnectDelayMs } from "@/api/runEvents";
import type { Run, RunEvent } from "@/api/types";

export type StreamState = "connecting" | "live" | "reconnecting" | "unsupported";

function handleRunEvent(client: QueryClient, event: RunEvent) {
  client.setQueryData<Run>(keys.run(event.run_id), (run) =>
    run === undefined ? run : applyRunEvent(run, event),
  );
  if (event.kind === "status") {
    void invalidateWithDashboard(client, keys.runLists, keys.automations);
  }
}

function connectStream(client: QueryClient, onState: (state: StreamState) => void): () => void {
  let source: EventSource | null = null;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let attempt = 0;
  const open = () => {
    source = new EventSource(apiUrl("/events"));
    source.onopen = () => {
      if (attempt > 0) {
        void client.invalidateQueries({ queryKey: keys.runs });
      }
      attempt = 0;
      onState("live");
    };
    source.onmessage = (message: MessageEvent<string>) => {
      const event = parseRunEvent(message.data);
      if (event !== null) {
        handleRunEvent(client, event);
      }
    };
    source.onerror = () => {
      source?.close();
      attempt += 1;
      onState("reconnecting");
      timer = setTimeout(open, reconnectDelayMs(attempt));
    };
  };
  open();
  return () => {
    clearTimeout(timer);
    source?.close();
  };
}

export function useRunEventStream(): StreamState {
  const client = useQueryClient();
  const supported = typeof EventSource !== "undefined";
  const [state, setState] = useState<StreamState>(supported ? "connecting" : "unsupported");
  useEffect(() => (supported ? connectStream(client, setState) : undefined), [client, supported]);
  return state;
}
