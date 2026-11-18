import { makeArtifact, makeRun, stagesWith } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { RunStatus, Upload, UploadStatus } from "@/api/types";
import {
  availableActions,
  defaultRetryStage,
  groupArtifacts,
  posterFor,
  retryStageOptions,
  stageProgress,
  uploadSummary,
  weightedScore,
} from "@/features/run-detail/model";
import { itemAt } from "../../helpers/itemAt";

const upload = (status: UploadStatus): Upload => ({
  target_id: "t",
  channel_id: "c",
  language: "en",
  variant: "episode",
  status,
  youtube_video_id: null,
  url: null,
  error: null,
  quota_units: 0,
});

describe("availableActions", () => {
  it.each<[RunStatus, string[]]>([
    ["queued", ["canCancel"]],
    ["running", ["canCancel"]],
    ["publishing", []],
    ["awaiting_review", ["canRetry", "canReview", "canDelete"]],
    ["approved", ["canRetry", "canPublish", "canDelete"]],
    ["failed", ["canRetry", "canDelete"]],
    ["published", ["canRetry", "canDelete"]],
  ])("allows the right actions for a %s run", (status, allowed) => {
    const actions = availableActions(makeRun({ status }));
    const enabled = Object.entries(actions)
      .filter(([, on]) => on)
      .map(([name]) => name);
    expect(enabled.sort()).toEqual([...allowed].sort());
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

  it("falls back to raw codes without a pipeline", () => {
    const run = makeRun({ artifacts: [makeArtifact({ language: "fr", variant: "reel" })] });
    expect(groupArtifacts(run)[0]?.title).toBe("fr — reel");
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
    expect(uploadSummary(uploads)).toEqual({ done: 2, failed: 1, pending: 2 });
  });
});
