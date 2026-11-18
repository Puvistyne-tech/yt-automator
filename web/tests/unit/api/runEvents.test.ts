import { makeArtifact, makeRun, stagesWith } from "@/api/mocks/fixtures/factories";
import {
  applyRunEvent,
  MAX_RUN_LOGS,
  parseRunEvent,
  reconnectDelayMs,
  runLogFromEvent,
} from "@/api/runEvents";
import type { JsonObject, RunEvent } from "@/api/types";

const AT = "2026-03-01T12:00:00Z";
const event = (kind: RunEvent["kind"], payload: JsonObject, run_id = "run-review"): RunEvent => ({
  run_id,
  kind,
  at: AT,
  payload,
});

describe("parseRunEvent", () => {
  it("parses a well formed event", () => {
    const data = JSON.stringify(event("status", { status: "running" }));
    expect(parseRunEvent(data)).toMatchObject({ run_id: "run-review", kind: "status" });
  });

  it.each(["not json", "[]", '{"kind":"status"}', '{"run_id":1,"kind":"x"}'])(
    "rejects %s",
    (data) => {
      expect(parseRunEvent(data)).toBeNull();
    },
  );
});

describe("applyRunEvent", () => {
  it("ignores events for another run", () => {
    const run = makeRun();
    expect(applyRunEvent(run, event("status", { status: "failed" }, "other"))).toBe(run);
  });

  it("updates status and error", () => {
    const next = applyRunEvent(makeRun(), event("status", { status: "failed", error: "No GPU" }));
    expect(next).toMatchObject({ status: "failed", error: "No GPU" });
  });

  it.each([[{ status: "failed" }], [{ status: "failed", error: 5 }]])(
    "keeps the previous error when the status payload %j has no text error",
    (payload) => {
      const run = makeRun({ status: "running", error: "old" });
      expect(applyRunEvent(run, event("status", payload))).toMatchObject({
        status: "failed",
        error: "old",
      });
    },
  );

  it("clears the error when a status event carries a null error", () => {
    const run = makeRun({ status: "failed", error: "old" });
    expect(applyRunEvent(run, event("status", { status: "queued", error: null }))).toMatchObject({
      status: "queued",
      error: null,
    });
  });

  it("keeps the run when a status event has no status", () => {
    const run = makeRun();
    expect(applyRunEvent(run, event("status", {}))).toBe(run);
  });

  it("replaces a known stage by id", () => {
    const run = makeRun({ stages: stagesWith(["running"]) });
    const stage = { ...run.stages[0], status: "done" } as JsonObject;
    const next = applyRunEvent(run, event("stage", stage));
    expect(next.stages[0]?.status).toBe("done");
    expect(next.stages).toHaveLength(run.stages.length);
  });

  it("appends a new artifact and replaces a known one", () => {
    const run = makeRun({ artifacts: [makeArtifact()] });
    const added = applyRunEvent(run, event("artifact", { ...makeArtifact({ id: "art-2" }) }));
    const replaced = applyRunEvent(run, event("artifact", { ...makeArtifact({ size_bytes: 1 }) }));
    expect(added.artifacts).toHaveLength(2);
    expect(replaced.artifacts).toEqual([makeArtifact({ size_bytes: 1 })]);
  });

  it("identifies uploads by target and variant", () => {
    const upload = {
      target_id: "target-en",
      variant: "episode",
      status: "uploading",
      youtube_video_id: null,
      url: null,
      error: null,
    };
    const first = applyRunEvent(makeRun(), event("upload", upload));
    const second = applyRunEvent(first, event("upload", { ...upload, status: "done" }));
    const other = applyRunEvent(second, event("upload", { ...upload, variant: "short" }));
    expect(second.uploads).toHaveLength(1);
    expect(second.uploads[0]?.status).toBe("done");
    expect(other.uploads).toHaveLength(2);
  });

  it("appends a log event to the run's stored logs", () => {
    const stored = {
      at: "2026-03-01T11:00:00Z",
      level: "info" as const,
      stage_id: null,
      message: "a",
    };
    const run = makeRun({ logs: [stored] });
    const next = applyRunEvent(
      run,
      event("log", { message: "b", level: "warning", stage_id: "story" }),
    );
    expect(next.logs).toEqual([
      stored,
      { at: AT, level: "warning", stage_id: "story", message: "b" },
    ]);
  });

  it("keeps the run when a log event has no message", () => {
    const run = makeRun();
    expect(applyRunEvent(run, event("log", { message: 3 }))).toBe(run);
  });

  it("keeps only the newest log entries", () => {
    const logs = Array.from({ length: MAX_RUN_LOGS }, (_, index) => ({
      at: AT,
      level: "info" as const,
      stage_id: null,
      message: `line ${index}`,
    }));
    const next = applyRunEvent(makeRun({ logs }), event("log", { message: "newest" }));
    expect(next.logs).toHaveLength(MAX_RUN_LOGS);
    expect(next.logs[0]?.message).toBe("line 1");
    expect(next.logs.at(-1)?.message).toBe("newest");
  });

  it("never keeps fewer log entries than the server returned", () => {
    const logs = Array.from({ length: MAX_RUN_LOGS + 5 }, (_, index) => ({
      at: AT,
      level: "info" as const,
      stage_id: null,
      message: `line ${index}`,
    }));
    const next = applyRunEvent(makeRun({ logs }), event("log", { message: "newest" }));
    expect(next.logs).toHaveLength(MAX_RUN_LOGS + 5);
    expect(next.logs[0]?.message).toBe("line 1");
  });
});

describe("runLogFromEvent", () => {
  it("builds a run log with defaults", () => {
    expect(runLogFromEvent(event("log", { message: "Rendering" }))).toEqual({
      at: AT,
      message: "Rendering",
      level: "info",
      stage_id: null,
    });
    expect(
      runLogFromEvent(event("log", { message: "Oops", level: "error", stage_id: "render" })),
    ).toMatchObject({ level: "error", stage_id: "render" });
  });

  it("treats an unknown level as info", () => {
    expect(runLogFromEvent(event("log", { message: "x", level: "debug" }))?.level).toBe("info");
  });

  it.each([event("status", { message: "x" }), event("log", { message: 3 })])(
    "returns null for %j",
    (input) => {
      expect(runLogFromEvent(input)).toBeNull();
    },
  );
});

describe("reconnectDelayMs", () => {
  it.each([
    [0, 1000],
    [1, 1000],
    [2, 2000],
    [4, 8000],
    [10, 30_000],
  ])("waits after attempt %d for %d ms", (attempt, ms) => {
    expect(reconnectDelayMs(attempt)).toBe(ms);
  });
});
