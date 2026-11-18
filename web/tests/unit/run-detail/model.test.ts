import { makeRun, makeUpload, stagesWith } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { RunStatus, UploadStatus } from "@/api/types";
import {
  availableActions,
  cancelMessage,
  defaultRetryStage,
  publishDescription,
  retryStageOptions,
  reviewMessage,
  reviewPayload,
  reviewRuleLabel,
  scoreTone,
  stageProgress,
  uploadAudience,
  uploadNote,
  uploadSummary,
  weightedScore,
} from "@/features/run-detail/model";

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

  it.each<[RunStatus, string]>([
    ["queued", "The run stops before it starts and is marked cancelled."],
    ["running", "The current stage stops and the run is marked cancelled."],
    ["awaiting_review", "The finished run is marked cancelled and will not be published."],
    ["approved", "The finished run is marked cancelled and will not be published."],
    ["failed", "The finished run is marked cancelled and will not be published."],
  ])("explains what cancelling a %s run does", (status, message) => {
    expect(cancelMessage(status)).toBe(message);
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

  it("labels the privacy and made-for-kids flag an upload was planned with", () => {
    expect(uploadAudience(makeUpload({ privacy: "unlisted", made_for_kids: true }))).toEqual({
      privacy: "Unlisted",
      madeForKids: "Yes",
    });
    expect(uploadAudience(makeUpload({ privacy: "public", made_for_kids: false }))).toEqual({
      privacy: "Public",
      madeForKids: "No",
    });
    expect(uploadAudience(makeUpload({ privacy: null, made_for_kids: null }))).toEqual({
      privacy: "—",
      madeForKids: "—",
    });
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
