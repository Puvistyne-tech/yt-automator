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

export function formatErrors(raw: JsonObject): Errors {
  if (raw.app !== EXPORT_APP) {
    return { app: `this file is not an ${EXPORT_APP} automation export` };
  }
  const version = raw.format_version;
  if (typeof version === "number" && version > EXPORT_FORMAT_VERSION) {
    return {
      format_version: `this file was exported by a newer ${EXPORT_APP} (format ${version}); this version reads format ${EXPORT_FORMAT_VERSION} and older, so update ${EXPORT_APP} to import it`,
    };
  }
  const automation = raw.automation;
  return typeof automation === "object" && automation !== null && !Array.isArray(automation)
    ? {}
    : { automation: "Field required" };
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
