import { db } from "@/api/mocks/db";
import { artifactsFor, STORY_ARTIFACT } from "@/api/mocks/fixtures/artifacts";
import { makeRun, makeTarget, stagesWith } from "@/api/mocks/fixtures/factories";
import { publishRun, skipReason } from "@/api/mocks/publish";
import { tick } from "@/api/mocks/simulator";
import type { ReviewPolicy } from "@/api/types";

const approved = (artifacts = artifactsFor("en", "episode")) =>
  makeRun({ status: "approved", languages: ["en"], artifacts });

describe("mock publish skip reasons", () => {
  it.each([
    [makeTarget({ language: "ta" }), "episode", "Language ta is not in this run."],
    [makeTarget({ channel_id: "gone" }), "episode", "The channel no longer exists."],
    [makeTarget(), "short", "No short video for en in this run."],
    [makeTarget(), "episode", null],
  ])("skips %j %s with %j", (target, variant, reason) => {
    expect(skipReason(approved(), target, variant)).toBe(reason);
  });
});

describe("mock publish outcome", () => {
  it("publishes when at least one upload is done", () => {
    const run = publishRun(approved());

    expect(run.status).toBe("published");
    expect(run.error).toBeNull();
    expect(run.uploads.map((upload) => upload.status)).toEqual(["done", "skipped", "skipped"]);
  });

  it("returns to approved when no upload succeeded", () => {
    const run = publishRun(approved([STORY_ARTIFACT]));

    expect(run.status).toBe("approved");
    expect(run.error).toBe("no upload succeeded");
    expect(run.uploads.every((upload) => upload.status === "skipped")).toBe(true);
  });
});

describe("mock simulator review policy", () => {
  const finishing = (review_policy: ReviewPolicy) =>
    makeRun({
      status: "running",
      score: null,
      review_policy,
      stages: stagesWith(["done", "done", "done", "done", "done", "done"]),
    });

  it.each([
    [{ mode: "always", min_score: 85 }, "awaiting_review"],
    [{ mode: "auto_when_score_at_least", min_score: 80 }, "approved"],
    [{ mode: "auto_when_score_at_least", min_score: 95 }, "awaiting_review"],
  ] as const)("finishes a run with policy %j as %s", (policy, status) => {
    db.state.runs = [finishing(policy)];

    tick();

    expect(db.state.runs[0]?.status).toBe(status);
  });
});

describe("mock simulator logs", () => {
  it("stores each stage log on the run and publishes it as an event", () => {
    const events: string[] = [];
    const unsubscribe = db.subscribe((event) => events.push(event.kind));
    db.state.runs = [makeRun({ status: "running", stages: stagesWith(["pending"]), logs: [] })];

    tick();
    unsubscribe();

    expect(db.state.runs[0]?.logs).toMatchObject([
      { level: "info", stage_id: "story", message: "Starting Write story" },
    ]);
    expect(events).toEqual(["stage", "log"]);
  });
});
