import type { Channel } from "@/api/types";

export function needsReconnect(channel: Channel): boolean {
  return channel.status !== "connected";
}

export function channelsNeedingReconnect(channelIds: string[], channels: Channel[]): Channel[] {
  const targeted = new Set(channelIds);
  return channels.filter((channel) => targeted.has(channel.id) && needsReconnect(channel));
}
