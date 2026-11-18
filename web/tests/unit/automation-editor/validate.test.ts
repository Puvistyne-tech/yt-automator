import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { Schedule } from "@/api/types";
import { draftFromAutomation } from "@/features/automation-editor/model/draft";
import {
  errorCounts,
  firstErrorSection,
  sectionAnchor,
  sectionOf,
} from "@/features/automation-editor/model/sections";
import {
  reviewErrors,
  scheduleErrors,
  validateDraft,
} from "@/features/automation-editor/model/validate";

const context = { pipeline: kidsStoryPipeline, channels: [makeChannel()], settingsErrors: {} };
const HOURS_ERROR = "Run at least every 1 hour, in whole hours.";
const schedule = (patch: Partial<Schedule>): Schedule => ({
  kind: "manual",
  every_hours: null,
  cron: null,
  timezone: "UTC",
  ...patch,
});

describe("validateDraft", () => {
  it("accepts a valid automation", () => {
    expect(validateDraft(draftFromAutomation(makeAutomation()), context)).toEqual({});
  });

  it("stops at general errors when the pipeline is unknown", () => {
    const draft = { ...draftFromAutomation(makeAutomation()), name: " ", pipeline_type: "gone" };
    expect(validateDraft(draft, { ...context, pipeline: undefined })).toEqual({
      name: "Give the automation a name.",
      pipeline_type: 'Unknown pipeline type "gone".',
    });
  });

  it("asks for a pipeline type when none is chosen", () => {
    const draft = { ...draftFromAutomation(makeAutomation()), pipeline_type: "" };
    expect(validateDraft(draft, { ...context, pipeline: undefined })).toEqual({
      pipeline_type: "Choose a pipeline type.",
    });
  });

  it("reports long names, missing languages, settings and every target problem", () => {
    const automation = makeAutomation({
      name: "x".repeat(121),
      languages: [],
      targets: [
        makeTarget({ channel_id: "", language: "", variants: [], publish_delay_minutes: -1 }),
      ],
    });
    const errors = validateDraft(draftFromAutomation(automation), {
      ...context,
      settingsErrors: { "": "Bad settings", "cast.0.name": "Required" },
    });
    expect(errors).toEqual({
      name: "Keep the name under 120 characters.",
      settings: "Bad settings",
      "settings.cast.0.name": "Required",
      languages: "Choose at least one language.",
      "targets.0.channel_id": "Choose a channel.",
      "targets.0.language": "Choose a language.",
      "targets.0.variants": "Choose at least one output.",
      "targets.0.publish_delay_minutes": "Use a whole number of minutes, 0 or more.",
    });
  });

  it("flags unknown languages, missing channels, unselected languages and unknown variants", () => {
    const automation = makeAutomation({
      languages: ["en", "fr"],
      targets: [makeTarget({ channel_id: "gone", language: "ta", variants: ["reel"] })],
    });
    expect(validateDraft(draftFromAutomation(automation), context)).toEqual({
      languages: "Kids story videos does not offer: fr.",
      "targets.0.channel_id": "This channel no longer exists.",
      "targets.0.language": "This language is not selected for the automation.",
      "targets.0.variants": "One of the outputs is not offered by this pipeline.",
    });
  });
});

describe("schedule and review rules", () => {
  it.each([
    [schedule({ kind: "interval", every_hours: 0 }), { "schedule.every_hours": HOURS_ERROR }],
    [schedule({ kind: "interval", every_hours: 1.5 }), { "schedule.every_hours": HOURS_ERROR }],
    [schedule({ kind: "interval", every_hours: null }), { "schedule.every_hours": HOURS_ERROR }],
    [schedule({ kind: "interval", every_hours: 6 }), {}],
    [
      schedule({ kind: "cron", cron: "0 25 * * *" }),
      { "schedule.cron": 'The hour field "25" is not valid.' },
    ],
    [schedule({ kind: "cron", cron: "0 18 * * *" }), {}],
    [schedule({ timezone: " " }), { "schedule.timezone": "Choose a timezone." }],
  ])("validates %j", (input, errors) => {
    expect(scheduleErrors(input)).toEqual(errors);
  });

  it.each([
    [{ mode: "always", min_score: 500 }, {}],
    [{ mode: "auto_when_score_at_least", min_score: 80 }, {}],
    [
      { mode: "auto_when_score_at_least", min_score: 101 },
      { "review_policy.min_score": "Use a score between 0 and 100." },
    ],
    [
      { mode: "auto_when_score_at_least", min_score: Number.NaN },
      { "review_policy.min_score": "Use a score between 0 and 100." },
    ],
  ] as const)("validates the review policy %j", (policy, errors) => {
    expect(reviewErrors(policy)).toEqual(errors);
  });
});

describe("editor sections", () => {
  it.each([
    ["name", "general"],
    ["pipeline_type", "general"],
    ["settings.cast.0.name", "content"],
    ["languages", "languages"],
    ["targets.1.channel_id", "targets"],
    ["schedule.cron", "schedule"],
    ["review_policy.min_score", "review"],
  ])("maps %s to the %s section", (path, section) => {
    expect(sectionOf(path)).toBe(section);
  });

  it("counts errors per section and finds the first one in display order", () => {
    const errors = { "schedule.cron": "x", "targets.0.language": "y", "targets.1.language": "z" };
    expect(errorCounts(errors)).toMatchObject({ targets: 2, schedule: 1, general: 0 });
    expect(firstErrorSection(errors)).toBe("targets");
    expect(firstErrorSection({})).toBeNull();
    expect(sectionAnchor("review")).toBe("editor-section-review");
  });
});
