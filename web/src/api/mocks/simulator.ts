import { afterApproval, autoRejected, scoredStatus } from "@/api/mocks/autoRules";
import { db } from "@/api/mocks/db";
import type { JsonObject, Run, RunEventKind, RunLog, StageRun } from "@/api/types";

function emit(run: Run, kind: RunEventKind, payload: JsonObject) {
  db.emit({ run_id: run.id, kind, at: db.now(), payload });
}

function logged(run: Run, entry: Omit<RunLog, "at">): Run {
  emit(run, "log", { ...entry });
  return { ...run, logs: [...run.logs, { ...entry, at: db.now() }] };
}

function replaceRun(run: Run) {
  db.state.runs = db.state.runs.map((item) => (item.id === run.id ? run : item));
}

function startRun(run: Run): Run {
  emit(run, "status", { status: "running" });
  return { ...run, status: "running", started_at: db.now() };
}

const SIMULATED_SCORE = 87.5;

function finishRun(run: Run): Run {
  const status = scoredStatus(run, SIMULATED_SCORE);
  const scored: Run = { ...run, status, score: SIMULATED_SCORE, finished_at: db.now() };
  const finished =
    status === "rejected" ? autoRejected(scored, SIMULATED_SCORE) : afterApproval(scored);
  emit(run, "status", { status: finished.status });
  return finished;
}

function stageUpdate(stage: StageRun, status: StageRun["status"]): StageRun {
  const now = db.now();
  return status === "running"
    ? { ...stage, status, provider: `fake-${stage.stage_id}`, started_at: now }
    : { ...stage, status, message: `${stage.title} finished`, finished_at: now };
}

function advanceStages(run: Run): Run {
  const active = run.stages.findIndex((stage) => stage.status === "running");
  const nextIndex = active === -1 ? run.stages.findIndex((s) => s.status === "pending") : active;
  const current = run.stages[nextIndex];
  if (current === undefined) {
    return finishRun(run);
  }
  const updated = stageUpdate(current, current.status === "running" ? "done" : "running");
  emit(run, "stage", updated as unknown as JsonObject);
  const message =
    updated.status === "running" ? `Starting ${updated.title}` : `${updated.title} complete`;
  const stages = run.stages.map((s, i) => (i === nextIndex ? updated : s));
  return logged({ ...run, stages }, { level: "info", stage_id: updated.stage_id, message });
}

function publishQueued(runId: string) {
  const run = db.state.runs.find((item) => item.id === runId);
  if (run !== undefined) {
    const published = afterApproval(run);
    emit(run, "status", { status: published.status });
    replaceRun(published);
  }
}

export function tick() {
  const queued = db.state.publishQueue.shift();
  if (queued !== undefined) {
    publishQueued(queued);
    return;
  }
  const run = db.state.runs.find((item) => item.status === "running" || item.status === "queued");
  if (run !== undefined) {
    replaceRun(run.status === "queued" ? startRun(run) : advanceStages(run));
  }
}

export function startSimulator(intervalMs = 2500): () => void {
  const timer = setInterval(tick, intervalMs);
  return () => clearInterval(timer);
}
