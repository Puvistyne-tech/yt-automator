import { needsReconnect } from "@/api/channelHealth";
import { db } from "@/api/mocks/db";

const DEFAULT_CONNECTED_CHANNEL = "chan-en";
const CONNECTED_PARAM = "connected";

function chosenChannelId(credentialId: string): string {
  const stale = db.state.channels.find(
    (channel) => channel.credential_id === credentialId && needsReconnect(channel),
  );
  return stale?.id ?? DEFAULT_CONNECTED_CHANNEL;
}

export function connectReturnUrl(credentialId: string): string {
  const query = new URLSearchParams({ [CONNECTED_PARAM]: chosenChannelId(credentialId) });
  return `${window.location.origin}/channels?${query.toString()}`;
}

export function completeConnectReturn(search: string): void {
  const channelId = new URLSearchParams(search).get(CONNECTED_PARAM);
  db.state.channels = db.state.channels.map((channel) =>
    channel.id === channelId ? { ...channel, status: "connected" } : channel,
  );
}
