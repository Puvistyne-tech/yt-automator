import type { ReviewPolicy, Run, RunStatus, ScoreItem, Upload } from "@/api/types";

export interface RunActions {
  canCancel: boolean;
  canRetry: boolean;
  canReview: boolean;
  canPublish: boolean;
  canDelete: boolean;
  showPublish: boolean;
}

export type Decision = "approved" | "rejected";

const CANCELLABLE: RunStatus[] = ["queued", "running", "awaiting_review", "approved"];
const RETRYABLE: RunStatus[] = ["failed", "cancelled", "awaiting_review", "approved", "rejected"];
const UNDELETABLE: RunStatus[] = ["queued", "running", "publishing"];

export const GOOD_SCORE = 85;
export const FAIR_SCORE = 60;

export function availableActions(run: Run): RunActions {
  const canPublish = run.status === "approved";
  return {
    canCancel: CANCELLABLE.includes(run.status),
    canRetry: RETRYABLE.includes(run.status),
    canReview: run.status === "awaiting_review",
    canPublish,
    canDelete: !UNDELETABLE.includes(run.status),
    showPublish: canPublish || run.status === "publishing" || run.uploads.length > 0,
  };
}

export function retryStageOptions(run: Run): { value: string; label: string }[] {
  return run.stages.map((stage, index) => ({
    value: stage.stage_id,
    label: `${index + 1}. ${stage.title}`,
  }));
}

export function defaultRetryStage(run: Run): string {
  return (run.stages.find((s) => s.status === "failed") ?? run.stages[0])?.stage_id ?? "";
}

export function reviewPayload(
  decision: Decision,
  notes: string,
): { decision: Decision; notes?: string } {
  const trimmed = notes.trim();
  return trimmed === "" ? { decision } : { decision, notes: trimmed };
}

export function reviewMessage(decision: Decision): string {
  return decision === "approved" ? "Run approved. You can publish it now." : "Run rejected.";
}

export function reviewRuleText(policy: ReviewPolicy): string {
  return policy.mode === "always" ? "always" : `auto-approve at ${policy.min_score}+`;
}

export function reviewRuleLabel(policy: ReviewPolicy): string {
  return `Review rule: ${reviewRuleText(policy)}`;
}

export function scoreTone(score: number): "success" | "warning" | "danger" {
  if (score >= GOOD_SCORE) {
    return "success";
  }
  return score >= FAIR_SCORE ? "warning" : "danger";
}

export function weightedScore(items: ScoreItem[]): number | null {
  const total = items.reduce((sum, item) => sum + item.weight, 0);
  if (items.length === 0 || total <= 0) {
    return null;
  }
  return items.reduce((sum, item) => sum + item.score * item.weight, 0) / total;
}

export type UploadCounts = Record<"done" | "failed" | "pending" | "skipped", number>;

export function uploadSummary(uploads: Upload[]): UploadCounts {
  const count = (...statuses: Upload["status"][]) =>
    uploads.filter((u) => statuses.includes(u.status)).length;
  return {
    done: count("done"),
    failed: count("failed"),
    pending: count("pending", "uploading"),
    skipped: count("skipped"),
  };
}

export function publishDescription(run: Run): string {
  if (run.uploads.length === 0) {
    return "Approved and ready. Publishing creates one upload per target and output.";
  }
  const summary = uploadSummary(run.uploads);
  const base = `${summary.done} uploaded · ${summary.failed} failed · ${summary.pending} pending`;
  return summary.skipped > 0 ? `${base} · ${summary.skipped} skipped` : base;
}

export function uploadNote(upload: Upload): { text: string; tone: "error" | "muted" } | null {
  if (upload.error === null || upload.error === "") {
    return null;
  }
  return { text: upload.error, tone: upload.status === "failed" ? "error" : "muted" };
}

export function stageProgress(run: Run): { done: number; total: number } {
  const done = run.stages.filter((s) => s.status === "done" || s.status === "skipped").length;
  return { done, total: run.stages.length };
}
