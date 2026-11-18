import { makeAutomation, makeChannel, makeTarget } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { LogLine } from "@/api/types";
import {
  languagesLabel,
  pipelineName,
  sortAutomations,
  targetsLabel,
} from "@/features/automation-list/summary";
import { mergeLogLines } from "@/features/run-detail/LogView";
import { hasActiveFilters, readFilters, withFilter } from "@/features/runs-list/filters";

describe("automation summary", () => {
  it("names pipelines and languages, falling back to ids", () => {
    expect(pipelineName([kidsStoryPipeline], "kutty_stories")).toBe("Kutty Stories");
    expect(pipelineName([], "other")).toBe("other");
    expect(languagesLabel(["en", "ta", "fr"], kidsStoryPipeline)).toBe("English, Tamil, fr");
    expect(languagesLabel([], kidsStoryPipeline)).toBe("—");
  });

  it.each([
    [[], "No targets"],
    [["a"], "A"],
    [["a", "a", "b"], "A, B"],
    [["a", "b", "c", "gone"], "A, B +2"],
  ])("labels targets on channels %j", (channelIds, label) => {
    const channels = ["a", "b", "c"].map((id) => makeChannel({ id, title: id.toUpperCase() }));
    const automation = makeAutomation({
      targets: channelIds.map((channel_id) => makeTarget({ channel_id })),
    });
    expect(targetsLabel(automation, channels)).toBe(label);
  });

  it("names a missing channel", () => {
    const automation = makeAutomation({ targets: [makeTarget({ channel_id: "gone" })] });
    expect(targetsLabel(automation, [])).toBe("Unknown channel");
  });

  it("sorts enabled automations first, then by name", () => {
    const sorted = sortAutomations([
      makeAutomation({ id: "1", name: "Zeta", enabled: true }),
      makeAutomation({ id: "2", name: "Alpha", enabled: false }),
      makeAutomation({ id: "3", name: "Beta", enabled: true }),
    ]);
    expect(sorted.map((a) => a.name)).toEqual(["Beta", "Zeta", "Alpha"]);
  });
});

describe("run filters", () => {
  it.each([
    ["", { limit: 100 }],
    ["status=failed", { status: "failed", limit: 100 }],
    ["status=bogus&automation_id=auto-1", { automation_id: "auto-1", limit: 100 }],
  ])("reads ?%s", (query, filters) => {
    expect(readFilters(new URLSearchParams(query))).toEqual(filters);
  });

  it("sets and clears a filter without touching the original", () => {
    const params = new URLSearchParams("status=failed");
    expect(withFilter(params, "automation_id", "a").toString()).toBe(
      "status=failed&automation_id=a",
    );
    expect(withFilter(params, "status", "").toString()).toBe("");
    expect(params.toString()).toBe("status=failed");
  });

  it("knows when a filter is active", () => {
    expect(hasActiveFilters({ limit: 100 })).toBe(false);
    expect(hasActiveFilters({ status: "queued", limit: 100 })).toBe(true);
  });
});

describe("mergeLogLines", () => {
  const line = (at: string, message: string, stage_id: string | null = "s"): LogLine => ({
    at,
    message,
    level: "info",
    stage_id,
  });

  it("drops stage lines repeated live and sorts by time", () => {
    const merged = mergeLogLines(
      [line("2026-01-01T00:00:03Z", "done"), line("2026-01-01T00:00:01Z", "start")],
      [line("2026-01-01T00:00:02Z", "done"), line("2026-01-01T00:00:04Z", "start", null)],
    );
    expect(merged.map((l) => `${l.at.slice(-3, -1)} ${l.message}`)).toEqual([
      "01 start",
      "02 done",
      "04 start",
    ]);
  });
});
