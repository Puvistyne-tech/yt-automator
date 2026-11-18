import type { FieldErrors } from "@/api/errors";
import type { Channel, PipelineDescriptor, ReviewPolicy, Schedule } from "@/api/types";
import type { AutomationDraft, TargetDraft } from "@/features/automation-editor/model/draft";
import { cronError } from "@/shared/format/cron";

export interface ValidationContext {
  pipeline: PipelineDescriptor | undefined;
  channels: Channel[];
  settingsErrors: Record<string, string>;
}

export const NAME_MAX_LENGTH = 120;

function generalErrors(draft: AutomationDraft, pipeline: PipelineDescriptor | undefined) {
  const errors: FieldErrors = {};
  const name = draft.name.trim();
  if (name === "") {
    errors.name = "Give the automation a name.";
  } else if (name.length > NAME_MAX_LENGTH) {
    errors.name = `Keep the name under ${NAME_MAX_LENGTH} characters.`;
  }
  if (draft.pipeline_type === "") {
    errors.pipeline_type = "Choose a pipeline type.";
  } else if (pipeline === undefined) {
    errors.pipeline_type = `Unknown pipeline type "${draft.pipeline_type}".`;
  }
  return errors;
}

function languageErrors(draft: AutomationDraft, pipeline: PipelineDescriptor) {
  const offered = new Set(pipeline.languages.map((l) => l.code));
  const unknown = draft.languages.filter((code) => !offered.has(code));
  if (draft.languages.length === 0) {
    return { languages: "Choose at least one language." };
  }
  return unknown.length > 0
    ? { languages: `${pipeline.name} does not offer: ${unknown.join(", ")}.` }
    : {};
}

function targetErrors(
  target: TargetDraft,
  index: number,
  draft: AutomationDraft,
  context: ValidationContext & { pipeline: PipelineDescriptor },
): FieldErrors {
  const errors: FieldErrors = {};
  const at = (field: string) => `targets.${index}.${field}`;
  if (!context.channels.some((channel) => channel.id === target.channel_id)) {
    errors[at("channel_id")] =
      target.channel_id === "" ? "Choose a channel." : "This channel no longer exists.";
  }
  if (!draft.languages.includes(target.language)) {
    errors[at("language")] =
      target.language === ""
        ? "Choose a language."
        : "This language is not selected for the automation.";
  }
  const variants = new Set(context.pipeline.variants.map((v) => v.id));
  if (target.variants.length === 0) {
    errors[at("variants")] = "Choose at least one output.";
  } else if (target.variants.some((v) => !variants.has(v))) {
    errors[at("variants")] = "One of the outputs is not offered by this pipeline.";
  }
  if (!Number.isInteger(target.publish_delay_minutes) || target.publish_delay_minutes < 0) {
    errors[at("publish_delay_minutes")] = "Use a whole number of minutes, 0 or more.";
  }
  return errors;
}

export function scheduleErrors(schedule: Schedule): FieldErrors {
  const errors: FieldErrors = {};
  const hours = schedule.every_hours;
  if (schedule.kind === "interval" && (hours === null || !Number.isInteger(hours) || hours < 1)) {
    errors["schedule.every_hours"] = "Run at least every 1 hour, in whole hours.";
  }
  if (schedule.kind === "cron") {
    const problem = cronError(schedule.cron ?? "");
    if (problem !== null) {
      errors["schedule.cron"] = problem;
    }
  }
  if (schedule.timezone.trim() === "") {
    errors["schedule.timezone"] = "Choose a timezone.";
  }
  return errors;
}

export function reviewErrors(policy: ReviewPolicy): FieldErrors {
  const score = policy.min_score;
  const invalid = !Number.isFinite(score) || score < 0 || score > 100;
  return policy.mode === "auto_when_score_at_least" && invalid
    ? { "review_policy.min_score": "Use a score between 0 and 100." }
    : {};
}

function settingsErrors(errors: Record<string, string>): FieldErrors {
  return Object.fromEntries(
    Object.entries(errors).map(([path, message]) => [
      path === "" ? "settings" : `settings.${path}`,
      message,
    ]),
  );
}

export function validateDraft(draft: AutomationDraft, context: ValidationContext): FieldErrors {
  const { pipeline } = context;
  const general = generalErrors(draft, pipeline);
  if (pipeline === undefined) {
    return general;
  }
  const scoped = { ...context, pipeline };
  return {
    ...general,
    ...settingsErrors(context.settingsErrors),
    ...languageErrors(draft, pipeline),
    ...Object.assign({}, ...draft.targets.map((t, i) => targetErrors(t, i, draft, scoped))),
    ...scheduleErrors(draft.schedule),
    ...reviewErrors(draft.review_policy),
  };
}
