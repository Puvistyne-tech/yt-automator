import { DEFAULT_REVIEW_POLICY, DEFAULT_SCHEDULE_LIMITS } from "@/api/automationDefaults";
import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { Schedule } from "@/api/types";
import { draftFromAutomation, type TargetDraft } from "@/features/automation-editor/model/draft";
import {
  NEEDS_PUBLIC,
  publishTimeErrors,
  retryErrors,
  reviewErrors,
  scheduleErrors,
  TIME_HINT,
} from "@/features/automation-editor/model/ruleErrors";
import { validateDraft } from "@/features/automation-editor/model/validate";

const schedule = (patch: Partial<Schedule>): Schedule => ({
  kind: "interval",
  every_hours: 6,
  cron: null,
  timezone: "UTC",
  ...DEFAULT_SCHEDULE_LIMITS,
  ...patch,
});

function targetDraft(patch: Partial<TargetDraft>): TargetDraft {
  const draft = draftFromAutomation(makeAutomation({ targets: [makeTarget()] }));
  const target = draft.targets[0];
  if (target === undefined) {
    throw new Error("fixture has a target");
  }
  return { ...target, ...patch };
}

const at = (field: string) => `targets.0.${field}`;

describe("schedule rule errors", () => {
  it.each([
    [schedule({ active_from: "08:00", active_until: "20:00" }), {}],
    [schedule({ active_from: "22:00", active_until: "06:00" }), {}],
    [schedule({ active_from: "8", active_until: "20:00" }), { "schedule.active_from": TIME_HINT }],
    [
      schedule({ active_from: "08:00", active_until: null }),
      { "schedule.active_until": TIME_HINT },
    ],
    [
      schedule({ active_from: "08:00", active_until: "08:00" }),
      { "schedule.active_until": "End the active hours at a different time than they start." },
    ],
    [schedule({ max_runs_per_day: 2 }), {}],
    [
      schedule({ max_runs_per_day: 0 }),
      { "schedule.max_runs_per_day": "Use a whole number of runs, 1 or more." },
    ],
    [
      schedule({ max_runs_per_day: 1.5 }),
      { "schedule.max_runs_per_day": "Use a whole number of runs, 1 or more." },
    ],
  ])("validates %j", (input, errors) => {
    expect(scheduleErrors(input)).toEqual(errors);
  });
});

describe("review rule errors", () => {
  const auto = { ...DEFAULT_REVIEW_POLICY, mode: "auto_when_score_at_least" as const };

  it.each([
    [{ ...DEFAULT_REVIEW_POLICY, reject_below: 95 }, {}],
    [{ ...auto, reject_below: 60 }, {}],
    [
      { ...auto, reject_below: 85 },
      { "review_policy.reject_below": "Keep this below the auto-approve score (85)." },
    ],
    [
      { ...DEFAULT_REVIEW_POLICY, reject_below: 120 },
      { "review_policy.reject_below": "Use a score between 0 and 100." },
    ],
    [
      { ...DEFAULT_REVIEW_POLICY, reject_below: Number.NaN },
      { "review_policy.reject_below": "Use a score between 0 and 100." },
    ],
  ])("validates %j", (input, errors) => {
    expect(reviewErrors(input)).toEqual(errors);
  });
});

describe("retry rule errors", () => {
  it.each([
    [{ auto_retry_count: 0, retry_delay_minutes: 10 }, {}],
    [{ auto_retry_count: 10, retry_delay_minutes: 1440 }, {}],
    [
      { auto_retry_count: 11, retry_delay_minutes: 10 },
      { "retry_policy.auto_retry_count": "Use a whole number from 0 to 10." },
    ],
    [
      { auto_retry_count: 1, retry_delay_minutes: -1 },
      { "retry_policy.retry_delay_minutes": "Use whole minutes from 0 to 1440." },
    ],
    [
      { auto_retry_count: 1, retry_delay_minutes: 1441 },
      { "retry_policy.retry_delay_minutes": "Use whole minutes from 0 to 1440." },
    ],
  ])("validates %j", (input, errors) => {
    expect(retryErrors(input)).toEqual(errors);
  });
});

describe("publish time errors", () => {
  it.each([
    [{}, {}],
    [{ publish_time_of_day: "18:00" }, {}],
    [{ publish_time_of_day: "6pm" }, { [at("publish_time_of_day")]: TIME_HINT }],
    [
      { publish_time_of_day: "18:00", publish_delay_minutes: 30 },
      { [at("publish_time_of_day")]: "Choose a delay or a time of day, not both." },
    ],
    [
      { publish_time_of_day: "18:00", privacy: "private" as const },
      { [at("publish_time_of_day")]: NEEDS_PUBLIC },
    ],
    [
      { publish_time_of_day: "18:00", publish_timezone: " " },
      { [at("publish_timezone")]: "Choose a timezone." },
    ],
    [
      { publish_delay_minutes: -1 },
      { [at("publish_delay_minutes")]: "Use a whole number of minutes, 0 or more." },
    ],
  ])("validates %j", (patch, errors) => {
    expect(publishTimeErrors(targetDraft(patch), at)).toEqual(errors);
  });

  it("is part of the whole-draft validation", () => {
    const draft = draftFromAutomation(makeAutomation());
    const target = targetDraft({ publish_time_of_day: "25:00" });
    const context = { pipeline: kidsStoryPipeline, channels: [makeChannel()], settingsErrors: {} };
    expect(validateDraft({ ...draft, targets: [target] }, context)).toEqual({
      [at("publish_time_of_day")]: TIME_HINT,
    });
  });
});
