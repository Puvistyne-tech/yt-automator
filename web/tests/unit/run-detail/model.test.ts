import { makeArtifact, makeRun, makeUpload, stagesWith } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { RunStatus, UploadStatus } from "@/api/types";
import {
  groupArtifacts,
  isTallArtifact,
  posterFor,
  splitGroup,
} from "@/features/run-detail/artifacts";
import {
  availableActions,
  defaultRetryStage,
  publishDescription,
  retryStageOptions,
  reviewMessage,
  reviewPayload,
  reviewRuleLabel,
  scoreTone,
  stageProgress,
  uploadNote,
  uploadSummary,
  weightedScore,
} from "@/features/run-detail/model";
import { itemAt } from "../../helpers/itemAt";

const upload = (status: UploadStatus) => makeUpload({ status });

describe("availableActions", () => {
  it.each<[RunStatus, string[]]>([
    ["queued", ["canCancel"]],
    ["running", ["canCancel"]],
    ["publishing", ["showPublish"]],
    ["awaiting_review", ["canCancel", "canRetry", "canReview", "canDelete"]],
    ["approved", ["canCancel", "canRetry", "canPublish", "canDelete", "showPublish"]],
    ["failed", ["canRetry", "canDelete"]],
    ["published", ["canDelete"]],
    ["rejected", ["canRetry", "canDelete"]],
    ["cancelled", ["canRetry", "canDelete"]],
  ])("allows the right actions for a %s run", (status, allowed) => {
    const actions = availableActions(makeRun({ status }));
    const enabled = Object.entries(actions)
      .filter(([, on]) => on)
      .map(([name]) => name);
    expect(enabled.sort()).toEqual([...allowed].sort());
  });

  it("shows the publish panel once a run has uploads", () => {
    const run = makeRun({ status: "published", uploads: [upload("done")] });
    expect(availableActions(run).showPublish).toBe(true);
  });
});

describe("retry stages", () => {
  it("numbers stages and defaults to the failed one, else the first", () => {
    const failed = makeRun({ stages: stagesWith(["done", "failed"]) });
    expect(retryStageOptions(failed)[1]?.label).toMatch(/^2\. /);
    expect(defaultRetryStage(failed)).toBe(failed.stages[1]?.stage_id);
    const fine = makeRun();
    expect(defaultRetryStage(fine)).toBe(fine.stages[0]?.stage_id);
    expect(defaultRetryStage(makeRun({ stages: [] }))).toBe("");
  });

  it("counts done and skipped stages as progress", () => {
    expect(stageProgress(makeRun({ stages: stagesWith(["done", "skipped", "running"]) }))).toEqual({
      done: 2,
      total: kidsStoryPipeline.stages.length,
    });
  });
});

describe("review", () => {
  it("sends trimmed notes only when there are some", () => {
    expect(reviewPayload("approved", "  ")).toEqual({ decision: "approved" });
    expect(reviewPayload("rejected", " Too dark ")).toEqual({
      decision: "rejected",
      notes: "Too dark",
    });
  });

  it("words the outcome and the review rule", () => {
    expect(reviewMessage("approved")).toBe("Run approved. You can publish it now.");
    expect(reviewMessage("rejected")).toBe("Run rejected.");
    expect(reviewRuleLabel({ mode: "always", min_score: 85 })).toBe("Review rule: always");
    expect(reviewRuleLabel({ mode: "auto_when_score_at_least", min_score: 85 })).toBe(
      "Review rule: auto-approve at 85+",
    );
  });

  it.each([
    [85, "success"],
    [84.9, "warning"],
    [60, "warning"],
    [59, "danger"],
  ])("tones a score of %d as %s", (score, tone) => {
    expect(scoreTone(score)).toBe(tone);
  });
});

describe("groupArtifacts", () => {
  it("groups by language and variant in run and pipeline order, shared first", () => {
    const run = makeRun({
      languages: ["ta", "en"],
      artifacts: [
        makeArtifact({ id: "a1", language: "en", variant: "short" }),
        makeArtifact({ id: "a2", language: "ta", variant: "episode" }),
        makeArtifact({ id: "a3", language: null, variant: null, kind: "text" }),
        makeArtifact({ id: "a4", language: "en", variant: "episode" }),
        makeArtifact({ id: "a5", language: "en", variant: "episode", kind: "thumbnail" }),
        makeArtifact({ id: "a6", language: "en", variant: null }),
      ],
    });
    const groups = groupArtifacts(run, kidsStoryPipeline);
    expect(groups.map((g) => g.title)).toEqual([
      "Shared across languages",
      "Tamil — Episode · 16:9",
      "English — All outputs",
      "English — Episode · 16:9",
      "English — Short · 9:16",
    ]);
    expect(groups[3]?.artifacts.map((a) => a.id)).toEqual(["a4", "a5"]);
    expect(posterFor(itemAt(groups, 3))?.id).toBe("a5");
    expect(posterFor(itemAt(groups, 1))).toBeUndefined();
  });

  it("names all-language groups and unknown variants, ordering unknowns last", () => {
    const run = makeRun({
      languages: ["en"],
      artifacts: [
        makeArtifact({ id: "b1", language: "fr", variant: "reel" }),
        makeArtifact({ id: "b2", language: "en", variant: "reel" }),
        makeArtifact({ id: "b3", language: null, variant: "episode" }),
      ],
    });
    expect(groupArtifacts(run, kidsStoryPipeline).map((g) => g.title)).toEqual([
      "All languages — Episode · 16:9",
      "English — reel",
      "fr — reel",
    ]);
  });

  it("falls back to raw codes without a pipeline", () => {
    const run = makeRun({ artifacts: [makeArtifact({ language: "fr", variant: "reel" })] });
    expect(groupArtifacts(run)[0]?.title).toBe("fr — reel");
  });

  it("splits a group into media, documents, captions and poster", () => {
    const run = makeRun({
      artifacts: [
        makeArtifact({ id: "v" }),
        makeArtifact({ id: "t", kind: "thumbnail" }),
        makeArtifact({ id: "s", kind: "subtitle" }),
        makeArtifact({ id: "m", kind: "metadata" }),
      ],
    });
    const parts = splitGroup(itemAt(groupArtifacts(run, kidsStoryPipeline), 0));
    expect(parts.media.map((a) => a.id)).toEqual(["v", "t"]);
    expect(parts.documents.map((a) => a.id)).toEqual(["s", "m"]);
    expect(parts.captions?.id).toBe("s");
    expect(parts.poster?.id).toBe("t");
  });

  it("decides tall previews from the variant aspect, then the frame size", () => {
    expect(isTallArtifact(makeArtifact({ variant: "short" }), kidsStoryPipeline)).toBe(true);
    expect(isTallArtifact(makeArtifact({ variant: "episode" }), kidsStoryPipeline)).toBe(false);
    const portrait = makeArtifact({ variant: "reel", meta: { width: 1080, height: 1920 } });
    expect(isTallArtifact(portrait, kidsStoryPipeline)).toBe(true);
    expect(isTallArtifact(makeArtifact({ variant: null, meta: {} }))).toBe(false);
  });
});

describe("scores and uploads", () => {
  it("weights scores and returns null without weight", () => {
    const item = (score: number, weight: number) => ({
      id: "x",
      title: "x",
      score,
      weight,
      detail: "",
    });
    expect(weightedScore([item(100, 3), item(60, 1)])).toBe(90);
    expect(weightedScore([])).toBeNull();
    expect(weightedScore([item(50, 0)])).toBeNull();
  });

  it("summarizes upload states", () => {
    const uploads = ["done", "done", "failed", "uploading", "pending", "skipped"].map((s) =>
      upload(s as UploadStatus),
    );
    expect(uploadSummary(uploads)).toEqual({ done: 2, failed: 1, pending: 2, skipped: 1 });
  });

  it("describes publishing before and after uploads", () => {
    expect(publishDescription(makeRun({ uploads: [] }))).toBe(
      "Approved and ready. Publishing creates one upload per target and output.",
    );
    expect(publishDescription(makeRun({ uploads: [upload("done")] }))).toBe(
      "1 uploaded · 0 failed · 0 pending",
    );
    expect(publishDescription(makeRun({ uploads: [upload("done"), upload("skipped")] }))).toBe(
      "1 uploaded · 0 failed · 0 pending · 1 skipped",
    );
  });

  it("shows failures as errors and skip reasons as notes", () => {
    expect(uploadNote(upload("done"))).toBeNull();
    expect(uploadNote(makeUpload({ status: "failed", error: "Quota" }))).toEqual({
      text: "Quota",
      tone: "error",
    });
    expect(uploadNote(makeUpload({ status: "skipped", error: "Not in run." }))).toEqual({
      text: "Not in run.",
      tone: "muted",
    });
  });
});
