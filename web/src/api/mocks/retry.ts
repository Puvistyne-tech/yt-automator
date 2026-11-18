import { validationFailed } from "@/api/mocks/db";
import type { Run, StageRun } from "@/api/types";

function retryStart(run: Run, fromStage: string | undefined): number | Response {
  if (fromStage !== undefined) {
    const index = run.stages.findIndex((stage) => stage.stage_id === fromStage);
    return index === -1
      ? validationFailed({ from_stage: `run has no stage '${fromStage}'` })
      : index;
  }
  const unfinished = run.stages.findIndex((stage) => stage.status !== "done");
  return Math.max(unfinished, 0);
}

function resetStage(stage: StageRun): StageRun {
  return {
    stage_id: stage.stage_id,
    title: stage.title,
    status: "pending",
    provider: "",
    message: "",
    started_at: null,
    finished_at: null,
  };
}

function reset(run: Run, start: number): Run {
  const resetIds = new Set(run.stages.slice(start).map((stage) => stage.stage_id));
  return {
    ...run,
    status: "queued",
    stages: run.stages.map((stage, index) => (index < start ? stage : resetStage(stage))),
    artifacts: run.artifacts.filter((artifact) => !resetIds.has(artifact.stage_id)),
    error: null,
    score: null,
    score_details: [],
    review: null,
    uploads: [],
    retry_at: null,
    auto_retries: 0,
    started_at: null,
    finished_at: null,
  };
}

export function retriedRun(run: Run, fromStage: string | undefined): Run | Response {
  const start = retryStart(run, fromStage);
  return start instanceof Response ? start : reset(run, start);
}
