import { isKidsPipeline } from "@/api/capabilities";
import type {
  Automation,
  AutomationInput,
  Channel,
  JsonObject,
  PipelineDescriptor,
  Privacy,
  ReviewPolicy,
  Schedule,
  ScheduleKind,
  Target,
} from "@/api/types";

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
  enabled: boolean;
}

export const DEFAULT_INTERVAL_HOURS = 24;
export const DEFAULT_CRON = "0 18 * * *";
export const DEFAULT_MIN_SCORE = 85;

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
    schedule: { kind: "manual", every_hours: null, cron: null, timezone },
    review_policy: { mode: "always", min_score: DEFAULT_MIN_SCORE },
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
    enabled: automation.enabled,
  };
}

export function initialDraft(
  pipelines: PipelineDescriptor[],
  automation: Automation | undefined,
  timezone = "UTC",
): AutomationDraft {
  if (automation !== undefined) {
    return draftFromAutomation(automation);
  }
  const only = pipelines.length === 1 ? pipelines[0] : undefined;
  const empty = emptyDraft(timezone);
  return only === undefined ? empty : applyPipeline(empty, only);
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
  };
}

export function withScheduleKind(schedule: Schedule, kind: ScheduleKind): Schedule {
  return {
    ...schedule,
    kind,
    every_hours:
      kind === "interval" ? (schedule.every_hours ?? DEFAULT_INTERVAL_HOURS) : schedule.every_hours,
    cron: kind === "cron" ? (schedule.cron ?? DEFAULT_CRON) : schedule.cron,
  };
}

export function withEveryHours(schedule: Schedule, hours: number): Schedule {
  return { ...schedule, every_hours: Number.isNaN(hours) ? null : hours };
}

export function normalizeSchedule(schedule: Schedule): Schedule {
  return {
    kind: schedule.kind,
    every_hours: schedule.kind === "interval" ? schedule.every_hours : null,
    cron: schedule.kind === "cron" ? (schedule.cron ?? "").trim() : null,
    timezone: schedule.timezone,
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
    enabled: draft.enabled,
  };
}

export function draftSignature(draft: AutomationDraft): string {
  return JSON.stringify({ ...draft, targets: draft.targets.map(({ key: _key, ...t }) => t) });
}
