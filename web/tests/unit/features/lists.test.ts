import {
  makeAutomation,
  makeChannel,
  makeRun,
  makeTarget,
  stagesWith,
} from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import {
  languagesLabel,
  nextRunLabel,
  pipelineName,
  reconnectWarning,
  sortAutomations,
  targetsLabel,
} from "@/features/automation-list/summary";
import { logRows } from "@/features/run-detail/logLines";
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

describe("reconnectWarning", () => {
  const channels = [
    makeChannel({ id: "a", title: "A" }),
    makeChannel({ id: "b", title: "B", status: "expired" }),
    makeChannel({ id: "c", title: "C", status: "revoked" }),
  ];
  const targeting = (...ids: string[]) =>
    makeAutomation({ targets: ids.map((channel_id) => makeTarget({ channel_id })) });

  it.each([
    [["a"], null],
    [[], null],
    [["a", "b"], "Reconnect B to keep publishing."],
    [["b", "c"], "Reconnect B, C to keep publishing."],
  ])("warns about targets on %j", (ids, warning) => {
    expect(reconnectWarning(targeting(...ids), channels)).toBe(warning);
  });
});

describe("nextRunLabel", () => {
  afterEach(() => vi.useRealTimers());

  it("says paused for a disabled automation", () => {
    expect(nextRunLabel(makeAutomation({ enabled: false }))).toBe("Paused");
  });

  it("shows a dash when an enabled automation has no next run", () => {
    expect(nextRunLabel(makeAutomation({ next_run_at: null }))).toBe("Next —");
  });

  it("shows how far ahead the next run is", () => {
    vi.useFakeTimers({ now: new Date("2026-03-01T12:00:00Z") });
    const automation = makeAutomation({ next_run_at: "2026-03-01T15:00:00Z" });
    expect(nextRunLabel(automation)).toBe("Next in 3 hours");
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

describe("logRows", () => {
  const AT = "2026-01-01T00:00:01Z";

  it("names each line's stage by its title, the run itself, or its id", () => {
    const run = makeRun({
      stages: stagesWith(["done"]),
      logs: [
        { at: AT, level: "info", stage_id: "story", message: "Wrote it" },
        { at: AT, level: "error", stage_id: null, message: "Run failed" },
        { at: AT, level: "warning", stage_id: "gone_stage", message: "Odd" },
      ],
    });
    expect(logRows(run).map((row) => [row.stage, row.level, row.message])).toEqual([
      ["Write story", "info", "Wrote it"],
      ["Run", "error", "Run failed"],
      ["Gone stage", "warning", "Odd"],
    ]);
  });

  it("gives repeated lines distinct keys", () => {
    const line = { at: AT, level: "info" as const, stage_id: null, message: "same" };
    const keys = logRows(makeRun({ logs: [line, line] })).map((row) => row.key);
    expect(new Set(keys).size).toBe(2);
  });

  it("returns nothing for a run without logs", () => {
    expect(logRows(makeRun({ logs: [] }))).toEqual([]);
  });
});
