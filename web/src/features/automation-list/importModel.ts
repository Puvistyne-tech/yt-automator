import { errorMessage, fieldErrorsOf, normalizeFieldErrors } from "@/api/errors";
import { channelOptionLabel } from "@/api/labels";
import type { Channel, ChannelChoices, ExportedChannel, JsonObject } from "@/api/types";
import { isJsonObject } from "@/shared/isJsonObject";
import type { SelectOption } from "@/shared/ui";

export const IMPORT_FILE_TYPES = ".json,application/json";
export const CHOOSE_CHANNEL = "";
export const LEAVE_OUT = "__leave_out__";
const GENERIC_FAILURE = "Validation failed";
const CHANNEL_PREFIX = "channel_map.";
const DOCUMENT_PREFIX = "automation.";
const NOT_AN_EXPORT = "This file is not an automation export: it does not hold a JSON object.";

export type ParsedFile = { document: JsonObject } | { error: string };

export interface ImportProblem {
  message: string | null;
  channels: Record<string, string>;
  fields: { label: string; message: string }[];
}

export function parseExportFile(text: string): ParsedFile {
  try {
    const parsed: unknown = JSON.parse(text);
    return isJsonObject(parsed) ? { document: parsed } : { error: NOT_AN_EXPORT };
  } catch {
    return { error: NOT_AN_EXPORT };
  }
}

export function channelChoiceOptions(channels: Channel[]): SelectOption[] {
  return [
    ...channels.map((channel) => ({ value: channel.id, label: channelOptionLabel(channel) })),
    { value: LEAVE_OUT, label: "Leave its targets out" },
  ];
}

export function channelMapFrom(choices: Record<string, string>): ChannelChoices {
  return Object.fromEntries(
    Object.entries(choices)
      .filter(([, value]) => value !== CHOOSE_CHANNEL)
      .map(([id, value]) => [id, value === LEAVE_OUT ? null : value]),
  );
}

export function exportedChannelName(channel: ExportedChannel): string {
  return channel.title === "" ? channel.id : channel.title;
}

export function fieldLabel(path: string): string {
  const text = path
    .replace(DOCUMENT_PREFIX, "")
    .split(".")
    .map((segment) => (/^\d+$/.test(segment) ? String(Number(segment) + 1) : segment))
    .join(" › ")
    .replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function importProblem(error: unknown): ImportProblem {
  const message = errorMessage(error);
  const entries = Object.entries(normalizeFieldErrors(fieldErrorsOf(error)));
  const channels = entries.filter(([path]) => path.startsWith(CHANNEL_PREFIX));
  const others = entries.filter(([path]) => !path.startsWith(CHANNEL_PREFIX));
  const generic = message === GENERIC_FAILURE;
  return {
    message: generic ? null : message,
    channels: Object.fromEntries(
      channels.map(([path, text]) => [path.slice(CHANNEL_PREFIX.length), text]),
    ),
    fields: generic
      ? others.map(([path, text]) => ({ label: fieldLabel(path), message: text }))
      : [],
  };
}
