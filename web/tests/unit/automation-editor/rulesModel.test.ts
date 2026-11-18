import { DEFAULT_REVIEW_POLICY, DEFAULT_SCHEDULE_LIMITS } from "@/api/automationDefaults";
import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { Schedule } from "@/api/types";
import {
  draftFromAutomation,
  emptyDraft,
  newTarget,
} from "@/features/automation-editor/model/draft";
import {
  DEFAULT_PUBLISH_DELAY_MINUTES,
  DEFAULT_PUBLISH_TIME,
  publishTiming,
  publishTimingFrom,
  publishTimingHint,
  SCHEDULED_PUBLISH_RULE,
  withPublishTiming,
} from "@/features/automation-editor/model/publishTiming";
import {
  defaultRejectBelow,
  withRejectBelow,
} from "@/features/automation-editor/model/reviewRules";
import {
  DEFAULT_ACTIVE_FROM,
  DEFAULT_ACTIVE_UNTIL,
  DEFAULT_DAILY_CAP,
  emptySchedule,
  normalizeSchedule,
  withActiveHours,
  withDailyCap,
} from "@/features/automation-editor/model/schedule";

const interval: Schedule = {
  kind: "interval",
  every_hours: 6,
  cron: null,
  timezone: "UTC",
  ...DEFAULT_SCHEDULE_LIMITS,
};

describe("schedule limits", () => {
  it("starts with safe defaults", () => {
    expect(emptySchedule("Asia/Kolkata")).toEqual({
      kind: "manual",
      every_hours: null,
      cron: null,
      timezone: "Asia/Kolkata",
      skip_if_unfinished: true,
      max_runs_per_day: null,
      active_from: null,
      active_until: null,
    });
    expect(emptyDraft().retry_policy).toEqual({ auto_retry_count: 0, retry_delay_minutes: 10 });
    expect(emptyDraft().review_policy).toEqual(DEFAULT_REVIEW_POLICY);
  });

  it("toggles active hours and the daily cap with named defaults", () => {
    const active = withActiveHours(interval, true);
    expect([active.active_from, active.active_until]).toEqual([
      DEFAULT_ACTIVE_FROM,
      DEFAULT_ACTIVE_UNTIL,
    ]);
    expect(withActiveHours(active, false)).toEqual(interval);
    expect(withDailyCap(interval, true).max_runs_per_day).toBe(DEFAULT_DAILY_CAP);
    expect(withDailyCap(withDailyCap(interval, true), false)).toEqual(interval);
  });

  it("sends blank active hours as null and keeps the limits", () => {
    const blank = { ...interval, active_from: " ", active_until: "20:00 ", max_runs_per_day: 3 };
    expect(normalizeSchedule(blank)).toMatchObject({
      active_from: null,
      active_until: "20:00",
      max_runs_per_day: 3,
      skip_if_unfinished: true,
    });
  });
});

describe("publish timing", () => {
  const target = draftFromAutomation(makeAutomation({ targets: [makeTarget()] })).targets[0];

  it.each([
    [{ publish_delay_minutes: 0, publish_time_of_day: null }, "upload"],
    [{ publish_delay_minutes: 15, publish_time_of_day: null }, "delay"],
    [{ publish_delay_minutes: 0, publish_time_of_day: "18:00" }, "time"],
  ] as const)("reads %j as %s", (fields, timing) => {
    expect(publishTiming(fields)).toBe(timing);
  });

  it("switches timing with defaults and never keeps both", () => {
    expect(withPublishTiming("upload")).toEqual({
      publish_delay_minutes: 0,
      publish_time_of_day: null,
    });
    expect(withPublishTiming("delay")).toEqual({
      publish_delay_minutes: DEFAULT_PUBLISH_DELAY_MINUTES,
      publish_time_of_day: null,
    });
    expect(withPublishTiming("time")).toEqual({
      publish_delay_minutes: 0,
      publish_time_of_day: DEFAULT_PUBLISH_TIME,
    });
    expect(publishTimingFrom("time")).toBe("time");
    expect(publishTimingFrom("soon")).toBe("upload");
  });

  it("explains the public-only rule and flags a private channel default", () => {
    if (target === undefined) {
      throw new Error("fixture has a target");
    }
    const timed = { ...target, publish_time_of_day: "18:00" };
    expect(publishTimingHint(target, makeChannel())).toBeUndefined();
    expect(publishTimingHint({ ...timed, privacy: "public" }, makeChannel())).toBe(
      SCHEDULED_PUBLISH_RULE,
    );
    expect(publishTimingHint(timed, makeChannel())).toBe(
      "The channel default is private, so this video is not scheduled. Set privacy to Public to use this.",
    );
    expect(publishTimingHint(timed, undefined)).toBe(SCHEDULED_PUBLISH_RULE);
  });

  it("gives new targets the schedule's time zone", () => {
    const draft = { ...emptyDraft("Asia/Kolkata"), languages: ["en"] };
    const created = newTarget(draft, kidsStoryPipeline, [makeChannel()]);
    expect(created).toMatchObject({ publish_time_of_day: null, publish_timezone: "Asia/Kolkata" });
  });
});

describe("review rules", () => {
  const auto = { ...DEFAULT_REVIEW_POLICY, mode: "auto_when_score_at_least" as const };

  it.each([
    [DEFAULT_REVIEW_POLICY, 50],
    [{ ...DEFAULT_REVIEW_POLICY, min_score: 30 }, 50],
    [{ ...auto, min_score: 85 }, 50],
    [{ ...auto, min_score: 40 }, 30],
    [{ ...auto, min_score: 5 }, 0],
  ])("suggests a reject score under %j", (policy, expected) => {
    expect(defaultRejectBelow(policy)).toBe(expected);
  });

  it("toggles auto-reject", () => {
    expect(withRejectBelow(DEFAULT_REVIEW_POLICY, true).reject_below).toBe(50);
    expect(
      withRejectBelow({ ...DEFAULT_REVIEW_POLICY, reject_below: 70 }, false).reject_below,
    ).toBe(null);
  });
});
