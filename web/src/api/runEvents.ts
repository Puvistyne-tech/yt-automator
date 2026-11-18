import type {
  Artifact,
  JsonObject,
  LogLevel,
  Run,
  RunEvent,
  RunLog,
  RunStatus,
  StageRun,
  Upload,
} from "@/api/types";

export const MAX_RUN_LOGS = 2000;

const LOG_LEVELS: readonly LogLevel[] = ["info", "warning", "error"];

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseRunEvent(data: string): RunEvent | null {
  try {
    const value: unknown = JSON.parse(data);
    if (isObject(value) && typeof value.run_id === "string" && typeof value.kind === "string") {
      return value as unknown as RunEvent;
    }
  } catch {
    return null;
  }
  return null;
}

function replaceBy<T>(items: T[], next: T, same: (item: T) => boolean): T[] {
  return items.some(same) ? items.map((item) => (same(item) ? next : item)) : [...items, next];
}

function applyStatus(run: Run, payload: JsonObject): Run {
  const status = payload.status as RunStatus | undefined;
  const error = typeof payload.error === "string" ? payload.error : run.error;
  return status === undefined ? run : { ...run, status, error };
}

function applyStage(run: Run, stage: StageRun): Run {
  return { ...run, stages: replaceBy(run.stages, stage, (s) => s.stage_id === stage.stage_id) };
}

function applyArtifact(run: Run, artifact: Artifact): Run {
  return { ...run, artifacts: replaceBy(run.artifacts, artifact, (a) => a.id === artifact.id) };
}

function applyUpload(run: Run, upload: Upload): Run {
  const same = (u: Upload) => u.target_id === upload.target_id && u.variant === upload.variant;
  return { ...run, uploads: replaceBy(run.uploads, upload, same) };
}

function applyLog(run: Run, event: RunEvent): Run {
  const entry = runLogFromEvent(event);
  return entry === null ? run : { ...run, logs: [...run.logs, entry].slice(-MAX_RUN_LOGS) };
}

export function applyRunEvent(run: Run, event: RunEvent): Run {
  if (event.run_id !== run.id) {
    return run;
  }
  switch (event.kind) {
    case "status":
      return applyStatus(run, event.payload);
    case "stage":
      return applyStage(run, event.payload as unknown as StageRun);
    case "artifact":
      return applyArtifact(run, event.payload as unknown as Artifact);
    case "upload":
      return applyUpload(run, event.payload as unknown as Upload);
    case "log":
      return applyLog(run, event);
    default:
      return run;
  }
}

function logLevelOf(value: unknown): LogLevel {
  return LOG_LEVELS.find((level) => level === value) ?? "info";
}

export function runLogFromEvent(event: RunEvent): RunLog | null {
  if (event.kind !== "log" || typeof event.payload.message !== "string") {
    return null;
  }
  return {
    at: event.at,
    level: logLevelOf(event.payload.level),
    stage_id: typeof event.payload.stage_id === "string" ? event.payload.stage_id : null,
    message: event.payload.message,
  };
}

export function reconnectDelayMs(attempt: number): number {
  return Math.min(30_000, 1000 * 2 ** Math.max(0, attempt - 1));
}
