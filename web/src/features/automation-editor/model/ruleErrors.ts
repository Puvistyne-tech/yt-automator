import { MAX_AUTO_RETRIES, MAX_RETRY_DELAY_MINUTES } from "@/api/automationDefaults";
import type { FieldErrors } from "@/api/errors";
import type { RetryPolicy, ReviewPolicy, Schedule } from "@/api/types";
import type { TargetDraft } from "@/features/automation-editor/model/draft";
import { cronError } from "@/shared/format/cron";
import { isIntegerAtLeast } from "@/shared/format/numbers";
import { isNotPublic, isTimeOfDay } from "@/shared/format/timeOfDay";

export const TIME_HINT = "Use a 24-hour time such as 08:00.";
export const NEEDS_PUBLIC = "A publish time only applies to public videos. Set privacy to Public.";

function isScore(value: number): boolean {
  return Number.isFinite(value) && value >= 0 && value <= 100;
}

function activeHoursErrors(schedule: Schedule): FieldErrors {
  const { active_from: from, active_until: until } = schedule;
  if (from === null && until === null) {
    return {};
  }
  const errors: FieldErrors = {};
  if (!isTimeOfDay(from)) {
    errors["schedule.active_from"] = TIME_HINT;
  }
  if (!isTimeOfDay(until)) {
    errors["schedule.active_until"] = TIME_HINT;
  } else if (from === until) {
    errors["schedule.active_until"] = "End the active hours at a different time than they start.";
  }
  return errors;
}

export function scheduleErrors(schedule: Schedule): FieldErrors {
  const errors: FieldErrors = activeHoursErrors(schedule);
  if (schedule.kind === "interval" && !isIntegerAtLeast(schedule.every_hours, 1)) {
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
  if (schedule.max_runs_per_day !== null && !isIntegerAtLeast(schedule.max_runs_per_day, 1)) {
    errors["schedule.max_runs_per_day"] = "Use a whole number of runs, 1 or more.";
  }
  return errors;
}

export function reviewErrors(policy: ReviewPolicy): FieldErrors {
  const auto = policy.mode === "auto_when_score_at_least";
  const errors: FieldErrors = {};
  if (auto && !isScore(policy.min_score)) {
    errors["review_policy.min_score"] = "Use a score between 0 and 100.";
  }
  const reject = policy.reject_below;
  if (reject !== null && !isScore(reject)) {
    errors["review_policy.reject_below"] = "Use a score between 0 and 100.";
  } else if (reject !== null && auto && reject >= policy.min_score) {
    errors["review_policy.reject_below"] =
      `Keep this below the auto-approve score (${policy.min_score}).`;
  }
  return errors;
}

export function retryErrors(policy: RetryPolicy): FieldErrors {
  const errors: FieldErrors = {};
  const count = policy.auto_retry_count;
  if (!isIntegerAtLeast(count, 0) || count > MAX_AUTO_RETRIES) {
    errors["retry_policy.auto_retry_count"] = `Use a whole number from 0 to ${MAX_AUTO_RETRIES}.`;
  }
  const delay = policy.retry_delay_minutes;
  if (!isIntegerAtLeast(delay, 0) || delay > MAX_RETRY_DELAY_MINUTES) {
    errors["retry_policy.retry_delay_minutes"] =
      `Use whole minutes from 0 to ${MAX_RETRY_DELAY_MINUTES}.`;
  }
  return errors;
}

export function publishTimeErrors(target: TargetDraft, at: (field: string) => string) {
  const errors: FieldErrors = {};
  if (!isIntegerAtLeast(target.publish_delay_minutes, 0)) {
    errors[at("publish_delay_minutes")] = "Use a whole number of minutes, 0 or more.";
  }
  const time = target.publish_time_of_day;
  if (time === null) {
    return errors;
  }
  if (!isTimeOfDay(time)) {
    errors[at("publish_time_of_day")] = TIME_HINT;
  } else if (target.publish_delay_minutes > 0) {
    errors[at("publish_time_of_day")] = "Choose a delay or a time of day, not both.";
  } else if (isNotPublic(target.privacy)) {
    errors[at("publish_time_of_day")] = NEEDS_PUBLIC;
  }
  if (target.publish_timezone.trim() === "") {
    errors[at("publish_timezone")] = "Choose a timezone.";
  }
  return errors;
}
