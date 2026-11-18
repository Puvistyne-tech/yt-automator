import { db } from "@/api/mocks/db";
import type { JsonObject, Run, RunEventKind, StageRun } from "@/api/types";

function emit(run: Run, kind: RunEventKind, payload: JsonObject) {
  db.emit({ run_id: run.id, kind, at: db.now(), payload });
}

function replaceRun(run: Run) {
  db.state.runs = db.state.runs.map((item) => (item.id === run.id ? run : item));
}

function startRun(run: Run): Run {
  emit(run, "status", { status: "running" });
  return { ...run, status: "running", started_at: db.now() };
}

function finishRun(run: Run): Run {
  emit(run, "status", { status: "awaiting_review" });
  return { ...run, status: "awaiting_review", score: 87.5, finished_at: db.now() };
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
  emit(run, "log", {
    stage_id: updated.stage_id,
    level: "info",
    message:
      updated.status === "running" ? `Starting ${updated.title}` : `${updated.title} complete`,
  });
  return { ...run, stages: run.stages.map((s, i) => (i === nextIndex ? updated : s)) };
}

export function tick() {
  const run = db.state.runs.find((item) => item.status === "running" || item.status === "queued");
  if (run !== undefined) {
    replaceRun(run.status === "queued" ? startRun(run) : advanceStages(run));
  }
}

export function startSimulator(intervalMs = 2500): () => void {
  const timer = setInterval(tick, intervalMs);
  return () => clearInterval(timer);
}
