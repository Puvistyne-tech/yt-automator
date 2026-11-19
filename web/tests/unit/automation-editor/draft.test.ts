import { DEFAULT_SCHEDULE_LIMITS } from "@/api/automationDefaults";
import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { PipelineDescriptor } from "@/api/types";
import {
  applyPipeline,
  draftFromAutomation,
  draftSignature,
  draftToInput,
  emptyDraft,
  initialDraft,
  newTarget,
} from "@/features/automation-editor/model/draft";
import {
  DEFAULT_CRON,
  DEFAULT_INTERVAL_HOURS,
  normalizeSchedule,
  withEveryHours,
  withScheduleKind,
} from "@/features/automation-editor/model/schedule";

const plainPipeline: PipelineDescriptor = {
  ...kidsStoryPipeline,
  type_id: "plain",
  capabilities: [],
  languages: [],
};

describe("draft model", () => {
  it("starts empty with a manual schedule in the given timezone", () => {
    expect(emptyDraft("Asia/Kolkata")).toMatchObject({
      name: "",
      pipeline_type: "",
      schedule: { kind: "manual", timezone: "Asia/Kolkata" },
      review_policy: { mode: "always" },
      enabled: true,
    });
  });

  it("applies a pipeline's defaults and first language", () => {
    const draft = applyPipeline(emptyDraft(), kidsStoryPipeline);
    expect(draft.pipeline_type).toBe("kids_story");
    expect(draft.settings).toEqual(kidsStoryPipeline.default_settings);
    expect(draft.settings).not.toBe(kidsStoryPipeline.default_settings);
    expect(draft.languages).toEqual(["en"]);
    expect(applyPipeline(emptyDraft(), plainPipeline).languages).toEqual([]);
  });

  it("chooses the only pipeline for a new automation and copies an existing one", () => {
    expect(initialDraft([kidsStoryPipeline], undefined).pipeline_type).toBe("kids_story");
    expect(initialDraft([kidsStoryPipeline, plainPipeline], undefined).pipeline_type).toBe("");
    const both = [kidsStoryPipeline, plainPipeline];
    expect(initialDraft(both, undefined, "UTC", plainPipeline.type_id).pipeline_type).toBe(
      plainPipeline.type_id,
    );
    expect(initialDraft(both, undefined, "UTC", "missing").pipeline_type).toBe("");
    const automation = makeAutomation();
    const draft = initialDraft([], automation);
    expect(draft.name).toBe(automation.name);
    expect(draft.targets[0]).toMatchObject({ id: "target-en", channel_id: "chan-en" });
    expect(draftFromAutomation(automation).targets[0]?.key).toMatch(/^target-draft-/);
  });

  it("adds a target on an unused channel with every variant and the kids lock", () => {
    const draft = { ...draftFromAutomation(makeAutomation()), languages: ["en"] };
    const channels = [makeChannel(), makeChannel({ id: "chan-ta" })];
    expect(newTarget(draft, kidsStoryPipeline, channels)).toMatchObject({
      id: undefined,
      channel_id: "chan-ta",
      language: "en",
      variants: ["episode", "short"],
      made_for_kids: true,
    });
    expect(newTarget(draft, plainPipeline, []).made_for_kids).toBeNull();
  });

  it("builds the API input with trimmed text, a locked kids flag and a clean schedule", () => {
    const automation = makeAutomation({
      name: "  Night  ",
      targets: [makeTarget({ made_for_kids: false })],
      schedule: {
        kind: "interval",
        every_hours: 6,
        cron: "0 1 * * *",
        timezone: "UTC",
        ...DEFAULT_SCHEDULE_LIMITS,
      },
    });
    const input = draftToInput(draftFromAutomation(automation), kidsStoryPipeline);
    expect(input.name).toBe("Night");
    expect(input.targets[0]).toEqual({ ...makeTarget(), made_for_kids: true });
    expect(input.schedule).toEqual({
      kind: "interval",
      every_hours: 6,
      cron: null,
      timezone: "UTC",
      ...DEFAULT_SCHEDULE_LIMITS,
    });
  });

  it("omits ids of new targets and keeps the flag for other pipelines", () => {
    const draft = applyPipeline(emptyDraft(), plainPipeline);
    const target = { ...newTarget(draft, plainPipeline, [makeChannel()]), made_for_kids: false };
    const input = draftToInput({ ...draft, targets: [target] }, plainPipeline);
    expect(input.targets[0]).not.toHaveProperty("id");
    expect(input.targets[0]?.made_for_kids).toBe(false);
  });

  it("ignores draft keys in the signature but tracks real changes", () => {
    const automation = makeAutomation();
    const draft = draftFromAutomation(automation);
    expect(draftSignature(draft)).toBe(draftSignature(draftFromAutomation(automation)));
    expect(draftSignature({ ...draft, name: "x" })).not.toBe(draftSignature(draft));
  });

  it("falls back to the first channel when every channel already has the language", () => {
    const draft = draftFromAutomation(makeAutomation({ languages: ["en"] }));
    expect(newTarget(draft, kidsStoryPipeline, [makeChannel()]).channel_id).toBe("chan-en");
  });

  it("leaves channel and language empty without channels or languages", () => {
    const draft = { ...draftFromAutomation(makeAutomation()), languages: [] };
    expect(newTarget(draft, kidsStoryPipeline, [])).toMatchObject({ channel_id: "", language: "" });
  });
});

describe("schedule model", () => {
  const manual = {
    kind: "manual" as const,
    every_hours: null,
    cron: null,
    timezone: "UTC",
    ...DEFAULT_SCHEDULE_LIMITS,
  };

  it("trims cron text and drops the interval for cron schedules", () => {
    expect(
      normalizeSchedule({ ...manual, kind: "cron", cron: " 0 8 * * * ", every_hours: 3 }),
    ).toEqual({ ...manual, kind: "cron", cron: "0 8 * * *", every_hours: null });
    expect(normalizeSchedule({ ...manual, kind: "cron" }).cron).toBe("");
  });

  it("fills named defaults when switching kind and keeps typed values", () => {
    expect(withScheduleKind(manual, "interval").every_hours).toBe(DEFAULT_INTERVAL_HOURS);
    expect(withScheduleKind(manual, "cron").cron).toBe(DEFAULT_CRON);
    expect(withScheduleKind({ ...manual, every_hours: 6 }, "interval").every_hours).toBe(6);
    expect(DEFAULT_INTERVAL_HOURS).toBe(24);
    expect(DEFAULT_CRON).toBe("0 18 * * *");
  });

  it("stores an empty interval as null", () => {
    expect(withEveryHours(manual, Number.NaN).every_hours).toBeNull();
    expect(withEveryHours(manual, 3).every_hours).toBe(3);
  });
});
