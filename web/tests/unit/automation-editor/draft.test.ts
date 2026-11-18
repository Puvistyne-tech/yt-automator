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
  isKidsPipeline,
  newTarget,
} from "@/features/automation-editor/model/draft";

const plainPipeline: PipelineDescriptor = {
  ...kidsStoryPipeline,
  type_id: "plain",
  capabilities: [],
  languages: [],
};

describe("draft model", () => {
  it("detects kids pipelines by capability", () => {
    expect(isKidsPipeline(kidsStoryPipeline)).toBe(true);
    expect(isKidsPipeline(plainPipeline)).toBe(false);
    expect(isKidsPipeline(undefined)).toBe(false);
  });

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
    expect(draft.pipeline_type).toBe("kutty_stories");
    expect(draft.settings).toEqual(kidsStoryPipeline.default_settings);
    expect(draft.settings).not.toBe(kidsStoryPipeline.default_settings);
    expect(draft.languages).toEqual(["en"]);
    expect(applyPipeline(emptyDraft(), plainPipeline).languages).toEqual([]);
  });

  it("chooses the only pipeline for a new automation and copies an existing one", () => {
    expect(initialDraft([kidsStoryPipeline], undefined).pipeline_type).toBe("kutty_stories");
    expect(initialDraft([kidsStoryPipeline, plainPipeline], undefined).pipeline_type).toBe("");
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
      schedule: { kind: "interval", every_hours: 6, cron: "0 1 * * *", timezone: "UTC" },
    });
    const input = draftToInput(draftFromAutomation(automation), kidsStoryPipeline);
    expect(input.name).toBe("Night");
    expect(input.targets[0]).toEqual({ ...makeTarget(), made_for_kids: true });
    expect(input.schedule).toEqual({
      kind: "interval",
      every_hours: 6,
      cron: null,
      timezone: "UTC",
    });
  });

  it("omits ids of new targets and keeps the flag for other pipelines", () => {
    const draft = applyPipeline(emptyDraft(), plainPipeline);
    const target = { ...newTarget(draft, plainPipeline, [makeChannel()]), made_for_kids: false };
    const input = draftToInput({ ...draft, targets: [target] }, plainPipeline);
    expect(input.targets[0]).not.toHaveProperty("id");
    expect(input.targets[0]?.made_for_kids).toBe(false);
  });

  it("ignores draft keys in the signature", () => {
    const automation = makeAutomation();
    expect(draftSignature(draftFromAutomation(automation))).toBe(
      draftSignature(draftFromAutomation(automation)),
    );
  });
});
