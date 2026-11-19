import { DEFAULT_RETRY_POLICY, DEFAULT_REVIEW_POLICY } from "@/api/automationDefaults";
import { isKidsPipeline } from "@/api/capabilities";
import type {
  Automation,
  AutomationInput,
  Channel,
  JsonObject,
  PipelineDescriptor,
  Privacy,
  RetryPolicy,
  ReviewPolicy,
  Schedule,
  Target,
} from "@/api/types";
import { emptySchedule, normalizeSchedule } from "@/features/automation-editor/model/schedule";

export interface TargetDraft {
  key: string;
  id: string | undefined;
  channel_id: string;
  language: string;
  variants: string[];
  privacy: Privacy | null;
  made_for_kids: boolean | null;
  playlist_id: string | null;
  publish_delay_minutes: number;
  publish_time_of_day: string | null;
  publish_timezone: string;
}

export interface AutomationDraft {
  name: string;
  description: string;
  pipeline_type: string;
  settings: JsonObject;
  languages: string[];
  targets: TargetDraft[];
  schedule: Schedule;
  review_policy: ReviewPolicy;
  retry_policy: RetryPolicy;
  enabled: boolean;
}

let keySeed = 0;

function nextKey(): string {
  keySeed += 1;
  return `target-draft-${keySeed}`;
}

export function emptyDraft(timezone = "UTC"): AutomationDraft {
  return {
    name: "",
    description: "",
    pipeline_type: "",
    settings: {},
    languages: [],
    targets: [],
    schedule: emptySchedule(timezone),
    review_policy: { ...DEFAULT_REVIEW_POLICY },
    retry_policy: { ...DEFAULT_RETRY_POLICY },
    enabled: true,
  };
}

export function applyPipeline(
  draft: AutomationDraft,
  pipeline: PipelineDescriptor,
): AutomationDraft {
  const first = pipeline.languages[0]?.code;
  return {
    ...draft,
    pipeline_type: pipeline.type_id,
    settings: structuredClone(pipeline.default_settings),
    languages: first === undefined ? [] : [first],
    targets: [],
  };
}

function targetDraft(target: Target): TargetDraft {
  return { ...target, key: nextKey(), variants: [...target.variants] };
}

export function draftFromAutomation(automation: Automation): AutomationDraft {
  return {
    name: automation.name,
    description: automation.description,
    pipeline_type: automation.pipeline_type,
    settings: structuredClone(automation.settings),
    languages: [...automation.languages],
    targets: automation.targets.map(targetDraft),
    schedule: { ...automation.schedule },
    review_policy: { ...automation.review_policy },
    retry_policy: { ...automation.retry_policy },
    enabled: automation.enabled,
  };
}

export function initialDraft(
  pipelines: PipelineDescriptor[],
  automation: Automation | undefined,
  timezone = "UTC",
  preferredType?: string,
): AutomationDraft {
  if (automation !== undefined) {
    return draftFromAutomation(automation);
  }
  const only = pipelines.length === 1 ? pipelines[0] : undefined;
  const chosen = pipelines.find((p) => p.type_id === preferredType) ?? only;
  const empty = emptyDraft(timezone);
  return chosen === undefined ? empty : applyPipeline(empty, chosen);
}

export function newTarget(
  draft: AutomationDraft,
  pipeline: PipelineDescriptor,
  channels: Channel[],
): TargetDraft {
  const used = new Set(draft.targets.map((t) => `${t.channel_id}:${t.language}`));
  const language = draft.languages[0] ?? "";
  const channel = channels.find((c) => !used.has(`${c.id}:${language}`)) ?? channels[0];
  return {
    key: nextKey(),
    id: undefined,
    channel_id: channel?.id ?? "",
    language,
    variants: pipeline.variants.map((v) => v.id),
    privacy: null,
    made_for_kids: isKidsPipeline(pipeline) ? true : null,
    playlist_id: null,
    publish_delay_minutes: 0,
    publish_time_of_day: null,
    publish_timezone: draft.schedule.timezone,
  };
}

export function draftToInput(
  draft: AutomationDraft,
  pipeline: PipelineDescriptor | undefined,
): AutomationInput {
  const kids = isKidsPipeline(pipeline);
  return {
    name: draft.name.trim(),
    description: draft.description.trim(),
    pipeline_type: draft.pipeline_type,
    settings: draft.settings,
    languages: draft.languages,
    targets: draft.targets.map(({ key: _key, id, ...target }) => ({
      ...(id === undefined ? {} : { id }),
      ...target,
      made_for_kids: kids ? true : target.made_for_kids,
    })),
    schedule: normalizeSchedule(draft.schedule),
    review_policy: draft.review_policy,
    retry_policy: draft.retry_policy,
    enabled: draft.enabled,
  };
}

export function draftSignature(draft: AutomationDraft): string {
  return JSON.stringify({ ...draft, targets: draft.targets.map(({ key: _key, ...t }) => t) });
}
