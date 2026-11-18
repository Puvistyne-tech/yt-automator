import { needsReconnect } from "@/api/channelHealth";
import { db } from "@/api/mocks/db";

const DEFAULT_CONNECTED_CHANNEL = "chan-en";

function reconnectedChannelId(credentialId: string): string {
  const stale = db.state.channels.find(
    (channel) => channel.credential_id === credentialId && needsReconnect(channel),
  );
  if (stale === undefined) {
    return DEFAULT_CONNECTED_CHANNEL;
  }
  db.state.channels = db.state.channels.map((channel) =>
    channel.id === stale.id ? { ...channel, status: "connected" } : channel,
  );
  return stale.id;
}

export function connectReturnUrl(credentialId: string): string {
  const query = new URLSearchParams({
    connected: reconnectedChannelId(credentialId),
    credential: credentialId,
  });
  return `${window.location.origin}/channels?${query.toString()}`;
}
