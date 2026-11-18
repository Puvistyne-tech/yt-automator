import type { MockStorage } from "@/api/mocks/fixtures/settings";
import { holdsRun, type PublishTargets } from "@/api/mocks/uploadHold";
import type {
  AppSettingsInput,
  Artifact,
  CleanupAction,
  CleanupItem,
  CleanupReport,
  Run,
  RunStatus,
} from "@/api/types";
import { isFinalOutput } from "@/shared/artifacts";

const DAY_MS = 86_400_000;
const PROTECTED = new Set<RunStatus>([
  "queued",
  "running",
  "awaiting_review",
  "approved",
  "publishing",
]);

export type RetentionPolicy = Pick<
  AppSettingsInput,
  "keep_runs_days" | "keep_intermediate_days"
> & {
  publish_targets: PublishTargets;
};

export interface RunUsage {
  final_bytes: number;
  intermediate_bytes: number;
}

function bytesOf(artifacts: Artifact[]): number {
  return artifacts.reduce((total, artifact) => total + artifact.size_bytes, 0);
}

export function runUsage(run: Run, workspaceBytes = 0): RunUsage {
  const finals = run.artifacts.filter(isFinalOutput);
  return {
    final_bytes: bytesOf(finals),
    intermediate_bytes: bytesOf(run.artifacts) - bytesOf(finals) + workspaceBytes,
  };
}

export function hasIntermediateWork(run: Run, workspaceBytes: number): boolean {
  return run.artifacts.some((artifact) => !isFinalOutput(artifact)) || workspaceBytes > 0;
}

function finishedTime(run: Run): number {
  return Date.parse(run.finished_at ?? run.created_at);
}

function isProtected(run: Run, now: number, policy: RetentionPolicy): boolean {
  const finished = finishedTime(run);
  const held = run.uploads.some((upload) =>
    holdsRun(upload, finished, now, policy.publish_targets),
  );
  const retrying = run.status === "failed" && run.retry_at !== null;
  return PROTECTED.has(run.status) || retrying || held;
}

function isOlderThan(run: Run, now: number, days: number): boolean {
  return days > 0 && now - finishedTime(run) >= days * DAY_MS;
}

export function cleanupAction(
  run: Run,
  now: number,
  policy: RetentionPolicy,
): CleanupAction | null {
  if (isProtected(run, now, policy)) {
    return null;
  }
  if (isOlderThan(run, now, policy.keep_runs_days)) {
    return "delete_run";
  }
  return isOlderThan(run, now, policy.keep_intermediate_days) ? "remove_intermediate" : null;
}

function runItem(run: Run, action: CleanupAction, usage: RunUsage): CleanupItem {
  return {
    run_id: run.id,
    action,
    automation_id: run.automation_id,
    automation_name: run.automation_name,
    status: run.status,
    finished_at: run.finished_at,
    bytes:
      action === "delete_run"
        ? usage.final_bytes + usage.intermediate_bytes
        : usage.intermediate_bytes,
  };
}

function plannedItem(run: Run, workspace: number, now: number, policy: RetentionPolicy) {
  const action = cleanupAction(run, now, policy);
  if (action === null) {
    return [];
  }
  if (action === "remove_intermediate" && !hasIntermediateWork(run, workspace)) {
    return [];
  }
  return [runItem(run, action, runUsage(run, workspace))];
}

export function cleanupItems(
  runs: Run[],
  storage: MockStorage,
  now: number,
  policy: RetentionPolicy,
): CleanupItem[] {
  const found = runs.flatMap((run) =>
    plannedItem(run, storage.workspace[run.id] ?? 0, now, policy),
  );
  const strays = storage.strays.map(
    (stray): CleanupItem => ({
      run_id: stray.run_id,
      action: "remove_orphan",
      automation_id: null,
      automation_name: "",
      status: null,
      finished_at: null,
      bytes: stray.bytes,
    }),
  );
  return [...found, ...strays];
}

export function cleanupReport(
  items: CleanupItem[],
  policy: RetentionPolicy,
  dryRun: boolean,
): CleanupReport {
  return {
    dry_run: dryRun,
    keep_runs_days: policy.keep_runs_days,
    keep_intermediate_days: policy.keep_intermediate_days,
    items,
    total_bytes: items.reduce((total, item) => total + item.bytes, 0),
  };
}

export function withoutIntermediate(run: Run, at: string, message: string): Run {
  return {
    ...run,
    artifacts: run.artifacts.filter(isFinalOutput),
    intermediate_removed_at: run.intermediate_removed_at ?? at,
    logs: [...run.logs, { at, level: "info", stage_id: null, message }],
  };
}
