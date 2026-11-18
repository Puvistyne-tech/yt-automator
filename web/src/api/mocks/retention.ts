import type { MockStorage } from "@/api/mocks/fixtures/settings";
import type {
  AppSettingsInput,
  Artifact,
  CleanupAction,
  CleanupItem,
  CleanupReport,
  Run,
  RunStatus,
} from "@/api/types";

const DAY_MS = 86_400_000;
const FINAL_KINDS = new Set(["video", "thumbnail", "subtitle", "metadata"]);
const PROTECTED = new Set<RunStatus>([
  "queued",
  "running",
  "awaiting_review",
  "approved",
  "publishing",
]);

export type RetentionPolicy = Pick<AppSettingsInput, "keep_runs_days" | "keep_intermediate_days">;

export function isFinalOutput(artifact: Artifact): boolean {
  return FINAL_KINDS.has(artifact.kind) && artifact.language !== null;
}

function bytesOf(artifacts: Artifact[]): number {
  return artifacts.reduce((total, artifact) => total + artifact.size_bytes, 0);
}

export function runUsage(run: Run): { final_bytes: number; intermediate_bytes: number } {
  const finals = run.artifacts.filter(isFinalOutput);
  return {
    final_bytes: bytesOf(finals),
    intermediate_bytes: bytesOf(run.artifacts) - bytesOf(finals),
  };
}

function isProtected(run: Run, now: number): boolean {
  const waiting = run.uploads.some(
    (upload) =>
      upload.status === "pending" ||
      upload.status === "uploading" ||
      (upload.publish_at !== null && Date.parse(upload.publish_at) > now),
  );
  return PROTECTED.has(run.status) || waiting;
}

function isOlderThan(run: Run, now: number, days: number): boolean {
  const finished = Date.parse(run.finished_at ?? run.created_at);
  return days > 0 && now - finished >= days * DAY_MS;
}

export function cleanupAction(
  run: Run,
  now: number,
  policy: RetentionPolicy,
): CleanupAction | null {
  if (isProtected(run, now)) {
    return null;
  }
  if (isOlderThan(run, now, policy.keep_runs_days)) {
    return "delete_run";
  }
  const working = runUsage(run).intermediate_bytes > 0;
  return working && isOlderThan(run, now, policy.keep_intermediate_days)
    ? "remove_intermediate"
    : null;
}

function runItem(run: Run, action: CleanupAction): CleanupItem {
  const usage = runUsage(run);
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

export function cleanupItems(
  runs: Run[],
  storage: MockStorage,
  now: number,
  policy: RetentionPolicy,
): CleanupItem[] {
  const found = runs.flatMap((run) => {
    const action = cleanupAction(run, now, policy);
    return action === null ? [] : [runItem(run, action)];
  });
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
