import { MAX_AUTO_RETRIES, MAX_RETRY_DELAY_MINUTES } from "@/api/automationDefaults";
import type {
  AutomationInput,
  RetryPolicy,
  ReviewPolicy,
  Schedule,
  TargetInput,
} from "@/api/types";
import { cronTimesOfDay } from "@/shared/format/cron";
import { isNotPublic, isTimeOfDay, minutesOfDay, withinHours } from "@/shared/format/timeOfDay";

const BOTH_ACTIVE_HOURS = "set both the start and the end of the active hours, or neither";
export const DELAY_OR_TIME = "choose a publish delay or a time of day, not both";
export const NEVER_STARTS = "the schedule never starts inside the active hours";
export const NEEDS_PUBLIC =
  "a publish time only applies to public videos: set privacy to Public or Channel default";

type Errors = Record<string, string>;

function knownZone(zone: string): boolean {
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone });
    return zone !== "";
  } catch {
    return false;
  }
}

function timeError(value: string | null, field: string): Errors {
  if (value === null || isTimeOfDay(value)) {
    return {};
  }
  return { [field]: `'${value}' is not a time of day: use a 24-hour time such as 08:00` };
}

function neverStarts(schedule: Schedule): boolean {
  const { active_from: from, active_until: until } = schedule;
  if (schedule.kind !== "cron" || !isTimeOfDay(from) || !isTimeOfDay(until)) {
    return false;
  }
  const window = [minutesOfDay(from), minutesOfDay(until)] as const;
  const times = cronTimesOfDay(schedule.cron ?? "");
  return times.length > 0 && !times.some((minute) => withinHours(minute, ...window));
}

function scheduleRuleErrors(schedule: Schedule): Errors {
  const { active_from: from, active_until: until } = schedule;
  const errors = {
    ...timeError(from, "schedule.active_from"),
    ...timeError(until, "schedule.active_until"),
  };
  if ((from === null) !== (until === null)) {
    errors[from === null ? "schedule.active_from" : "schedule.active_until"] ??= BOTH_ACTIVE_HOURS;
  } else if (from !== null && from === until) {
    errors["schedule.active_until"] ??= "must differ from the start of the active hours";
  }
  if (schedule.max_runs_per_day !== null && schedule.max_runs_per_day < 1) {
    errors["schedule.max_runs_per_day"] = "Input should be greater than or equal to 1";
  }
  if (Object.keys(errors).length === 0 && neverStarts(schedule)) {
    errors["schedule.active_from"] = NEVER_STARTS;
  }
  return errors;
}

function reviewRuleErrors(policy: ReviewPolicy): Errors {
  const auto = policy.mode === "auto_when_score_at_least";
  if (auto && policy.reject_below !== null && policy.reject_below >= policy.min_score) {
    return {
      "review_policy.reject_below": `must be below the minimum score for auto-approval (${policy.min_score})`,
    };
  }
  return {};
}

function bound(value: number, max: number, field: string): Errors {
  if (value < 0) {
    return { [field]: "Input should be greater than or equal to 0" };
  }
  return value > max ? { [field]: `Input should be less than or equal to ${max}` } : {};
}

function retryRuleErrors(policy: RetryPolicy): Errors {
  return {
    ...bound(policy.auto_retry_count, MAX_AUTO_RETRIES, "retry_policy.auto_retry_count"),
    ...bound(
      policy.retry_delay_minutes,
      MAX_RETRY_DELAY_MINUTES,
      "retry_policy.retry_delay_minutes",
    ),
  };
}

function publishTimeErrors(target: TargetInput, index: number): Errors {
  const at = (field: string) => `targets.${index}.${field}`;
  const errors: Errors = knownZone(target.publish_timezone)
    ? {}
    : { [at("publish_timezone")]: `unknown timezone '${target.publish_timezone}'` };
  const time = target.publish_time_of_day;
  if (time === null) {
    return errors;
  }
  Object.assign(errors, timeError(time, at("publish_time_of_day")));
  if (target.publish_delay_minutes > 0) {
    errors[at("publish_time_of_day")] ??= DELAY_OR_TIME;
  }
  if (isNotPublic(target.privacy)) {
    errors[at("publish_time_of_day")] ??= NEEDS_PUBLIC;
  }
  return errors;
}

export function automationRuleErrors(input: AutomationInput): Errors {
  return {
    ...scheduleRuleErrors(input.schedule),
    ...reviewRuleErrors(input.review_policy),
    ...retryRuleErrors(input.retry_policy),
    ...Object.assign({}, ...input.targets.map(publishTimeErrors)),
  };
}
