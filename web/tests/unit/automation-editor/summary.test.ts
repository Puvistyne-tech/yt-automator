import {
  DEFAULT_RETRY_POLICY,
  DEFAULT_REVIEW_POLICY,
  DEFAULT_SCHEDULE_LIMITS,
} from "@/api/automationDefaults";
import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import type { ReviewPolicy, Schedule } from "@/api/types";
import { draftFromAutomation } from "@/features/automation-editor/model/draft";
import {
  automationSummary,
  privacyWord,
  retryPhrase,
  reviewPhrase,
  schedulePhrase,
} from "@/features/automation-editor/model/summary";

const schedule = (patch: Partial<Schedule>): Schedule => ({
  kind: "interval",
  every_hours: 6,
  cron: null,
  timezone: "UTC",
  ...DEFAULT_SCHEDULE_LIMITS,
  ...patch,
});
const policy = (patch: Partial<ReviewPolicy>): ReviewPolicy => ({
  ...DEFAULT_REVIEW_POLICY,
  ...patch,
});
const channels = [makeChannel()];

describe("automationSummary", () => {
  it("reads like the owner's example", () => {
    const automation = makeAutomation({
      schedule: schedule({ active_from: "08:00", active_until: "20:00", max_runs_per_day: 2 }),
      review_policy: policy({ auto_publish: true }),
      targets: [makeTarget({ privacy: null })],
    });
    expect(automationSummary(draftFromAutomation(automation), channels)).toBe(
      "Runs every 6 hours, 08:00 to 20:00, at most 2 a day. Publishes privately after you approve.",
    );
  });

  it("adds retries and auto-rejects between the schedule and the publish rule", () => {
    const automation = makeAutomation({
      schedule: schedule({ kind: "manual" }),
      retry_policy: { auto_retry_count: 2, retry_delay_minutes: 15 },
      review_policy: policy({ reject_below: 50 }),
      targets: [makeTarget({ privacy: "public" })],
    });
    expect(automationSummary(draftFromAutomation(automation), channels)).toBe(
      "Runs only when you press Run now. Retries a failed run up to 2 times, after 15 minutes. " +
        "Rejects runs scoring under 50. Publishes publicly when you press Publish after approval.",
    );
  });
});

describe("summary phrases", () => {
  it.each([
    [schedule({}), "Runs every 6 hours."],
    [schedule({ every_hours: 24 }), "Runs every day."],
    [schedule({ kind: "cron", cron: "0 18 * * *" }), "Runs every day at 18:00."],
    [
      schedule({ kind: "cron", cron: "0 18 * * *", timezone: "Asia/Kolkata" }),
      "Runs every day at 18:00 (Asia/Kolkata).",
    ],
    [schedule({ kind: "cron", cron: "0 9 1-7 * 1" }), 'Runs on cron "0 9 1-7 * 1".'],
    [
      schedule({ timezone: "Asia/Kolkata", active_from: "22:00", active_until: "06:00" }),
      "Runs every 6 hours, 22:00 to 06:00 (Asia/Kolkata).",
    ],
    [schedule({ max_runs_per_day: 1 }), "Runs every 6 hours, at most once a day."],
    [schedule({ skip_if_unfinished: false }), "Runs every 6 hours. Scheduled runs may overlap."],
  ])("describes %j", (input, text) => {
    expect(schedulePhrase(input)).toBe(text);
  });

  it.each([
    [DEFAULT_RETRY_POLICY, ""],
    [{ auto_retry_count: 1, retry_delay_minutes: 1 }, "Retries a failed run once, after 1 minute."],
    [
      { auto_retry_count: 3, retry_delay_minutes: 0 },
      "Retries a failed run up to 3 times, right away.",
    ],
  ])("describes retries %j", (input, text) => {
    expect(retryPhrase(input)).toBe(text);
  });

  it.each([
    [policy({}), "Publishes privately when you press Publish after approval."],
    [
      policy({ mode: "auto_when_score_at_least" }),
      "Approves runs scoring 85 or more. Publishes privately when you press Publish after approval.",
    ],
    [
      policy({ mode: "auto_when_score_at_least", auto_publish: true }),
      "Publishes privately when the score reaches 85, otherwise after you approve.",
    ],
  ])("describes review %j", (input, text) => {
    expect(reviewPhrase(input, "privately")).toBe(text);
  });

  it("says nothing publishes without targets", () => {
    expect(reviewPhrase(policy({ reject_below: 40 }), null)).toBe(
      "Rejects runs scoring under 40. Nothing publishes until you add a target.",
    );
  });

  it("words the privacy of the targets", () => {
    const draft = draftFromAutomation(makeAutomation());
    const target = draft.targets[0];
    if (target === undefined) {
      throw new Error("fixture has a target");
    }
    expect(privacyWord([], channels)).toBeNull();
    expect(privacyWord([target], channels)).toBe("privately");
    expect(privacyWord([target], [])).toBe("with the channel default");
    expect(privacyWord([{ ...target, privacy: "unlisted" }], [])).toBe("as unlisted");
    const mixed = [target, { ...target, privacy: "public" as const }];
    expect(privacyWord(mixed, channels)).toBe("with each target's privacy");
  });
});
