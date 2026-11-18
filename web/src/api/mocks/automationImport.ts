import {
  DEFAULT_RETRY_POLICY,
  DEFAULT_REVIEW_POLICY,
  DEFAULT_SCHEDULE_LIMITS,
} from "@/api/automationDefaults";
import type {
  Automation,
  AutomationDocument,
  AutomationInput,
  Channel,
  ChannelChoices,
  ExportedChannel,
  ImportPreview,
  JsonObject,
  PipelineDescriptor,
} from "@/api/types";
import { isJsonObject } from "@/shared/isJsonObject";

export const EXPORT_APP = "AutoTube";
export const EXPORT_FORMAT_VERSION = 1;

type Errors = Record<string, string>;
type Exported = AutomationDocument["automation"];

export function exportDocument(automation: Automation, channels: Channel[]): AutomationDocument {
  const { id: _id, created_at, updated_at, next_run_at, last_run, enabled, ...fields } = automation;
  const used = new Set(automation.targets.map((target) => target.channel_id));
  return {
    app: EXPORT_APP,
    format_version: EXPORT_FORMAT_VERSION,
    exported_at: new Date().toISOString(),
    automation: { ...fields, targets: automation.targets.map(({ id: _target, ...rest }) => rest) },
    channels: channels
      .filter((channel) => used.has(channel.id))
      .map(({ id, youtube_channel_id, title }) => ({ id, youtube_channel_id, title })),
  };
}

function formatErrors(raw: JsonObject): Errors {
  if (raw.app !== EXPORT_APP) {
    return { app: `this file is not an ${EXPORT_APP} automation export` };
  }
  const version = raw.format_version;
  if (typeof version === "number" && version > EXPORT_FORMAT_VERSION) {
    return {
      format_version: `this file was exported by a newer ${EXPORT_APP} (format ${version}); this version reads format ${EXPORT_FORMAT_VERSION} and older, so update ${EXPORT_APP} to import it`,
    };
  }
  return isJsonObject(raw.automation) ? {} : { automation: "Field required" };
}

const EXTRA_KEY = "Extra inputs are not permitted";
const DOCUMENT_KEYS = ["app", "format_version", "exported_at", "automation", "channels"];
const CHANNEL_KEYS = ["id", "youtube_channel_id", "title"];
const AUTOMATION_KEYS = [
  ...["name", "description", "pipeline_type", "settings", "languages", "enabled"],
  ...["schedule", "review_policy", "retry_policy", "targets"],
];
const TARGET_KEYS = [
  ...["channel_id", "language", "variants", "privacy", "made_for_kids", "playlist_id"],
  ...["publish_delay_minutes", "publish_time_of_day", "publish_timezone"],
];

function extraKeys(value: unknown, allowed: string[], path: string): Errors {
  const keys = isJsonObject(value) ? Object.keys(value) : [];
  return Object.fromEntries(
    keys.filter((key) => !allowed.includes(key)).map((key) => [`${path}${key}`, EXTRA_KEY]),
  );
}

function listedExtraKeys(value: unknown, allowed: string[], path: string): Errors {
  const items = Array.isArray(value) ? value : [];
  return Object.assign(
    {},
    ...items.map((item, index) => extraKeys(item, allowed, `${path}${index}.`)),
  );
}

export function documentErrors(raw: JsonObject): Errors {
  const format = formatErrors(raw);
  if (Object.keys(format).length > 0) {
    return format;
  }
  const automation = raw.automation as JsonObject;
  return {
    ...extraKeys(raw, DOCUMENT_KEYS, ""),
    ...listedExtraKeys(raw.channels, CHANNEL_KEYS, "channels."),
    ...extraKeys(automation, AUTOMATION_KEYS, "automation."),
    ...listedExtraKeys(automation.targets, TARGET_KEYS, "automation.targets."),
  };
}

export function refusalMessage(errors: Errors): string {
  const reason = errors.format_version ?? errors.app;
  return reason === undefined ? "Validation failed" : `This file cannot be imported: ${reason}.`;
}

function exportedChannel(document: AutomationDocument, id: string): ExportedChannel {
  return (
    document.channels?.find((item) => item.id === id) ?? { id, youtube_channel_id: "", title: "" }
  );
}

function localChannel(document: AutomationDocument, id: string, channels: Channel[]) {
  if (channels.some((channel) => channel.id === id)) {
    return id;
  }
  const youtubeId = exportedChannel(document, id).youtube_channel_id;
  return channels.find((c) => youtubeId !== "" && c.youtube_channel_id === youtubeId)?.id;
}

export function resolvedChannels(
  document: AutomationDocument,
  channels: Channel[],
  chosen: ChannelChoices,
): ChannelChoices {
  const ids = [...new Set(document.automation.targets.map((target) => target.channel_id))];
  return Object.fromEntries(
    ids.flatMap((id) => {
      const local = id in chosen ? chosen[id] : localChannel(document, id, channels);
      return local === undefined ? [] : [[id, local]];
    }),
  );
}

function importedInput(source: Exported, mapping: ChannelChoices, pipeline?: PipelineDescriptor) {
  const targets = source.targets
    .filter((target) => mapping[target.channel_id] !== null)
    .map((target) => ({ ...target, channel_id: mapping[target.channel_id] ?? target.channel_id }));
  const input: AutomationInput = {
    ...source,
    name: `${source.name} (imported)`,
    settings: { ...(pipeline?.default_settings ?? {}), ...source.settings },
    schedule: { ...DEFAULT_SCHEDULE_LIMITS, ...source.schedule },
    review_policy: { ...DEFAULT_REVIEW_POLICY, ...source.review_policy },
    retry_policy: { ...DEFAULT_RETRY_POLICY, ...source.retry_policy },
    enabled: false,
    targets,
  };
  return input;
}

export function importPreview(
  document: AutomationDocument,
  channels: Channel[],
  chosen: ChannelChoices,
  pipelines: PipelineDescriptor[],
): ImportPreview {
  const mapping = resolvedChannels(document, channels, chosen);
  const pipeline = pipelines.find((p) => p.type_id === document.automation.pipeline_type);
  const ids = [...new Set(document.automation.targets.map((target) => target.channel_id))];
  return {
    automation: importedInput(document.automation, mapping, pipeline),
    unknown_channels: ids
      .filter((id) => !(id in mapping))
      .map((id) => exportedChannel(document, id)),
  };
}

export function choiceErrors(chosen: ChannelChoices, channels: Channel[]): Errors {
  return Object.fromEntries(
    Object.entries(chosen)
      .filter(([, local]) => local !== null && !channels.some((channel) => channel.id === local))
      .map(([exported, local]) => [`channel_map.${exported}`, `channel '${local}' does not exist`]),
  );
}

export function missingChoiceErrors(unknown: ExportedChannel[]): Errors {
  return Object.fromEntries(
    unknown.map((item) => [
      `channel_map.${item.id}`,
      `channel '${item.title || item.id}' is not connected here: choose a channel for its targets or leave them out`,
    ]),
  );
}
