import {
  AUTO_PUBLISH_STOPPED_PREFIX,
  AUTO_REJECT_PREFIX,
  AUTO_RETRY_PREFIX,
  skippedStartTime,
} from "@/api/automaticEvents";
import type { Run, RunLog } from "@/api/types";
import { formatDateTime } from "@/shared/format/dates";

export interface AutomaticEvent {
  key: string;
  tone: "info" | "warning" | "danger";
  title: string;
  detail: string;
}

function rejection(run: Run): AutomaticEvent[] {
  const review = run.review;
  if (review === null || !review.notes.startsWith(AUTO_REJECT_PREFIX)) {
    return [];
  }
  return [
    { key: "rejected", tone: "danger", title: "Rejected automatically", detail: review.notes },
  ];
}

function pendingRetry(run: Run): AutomaticEvent[] {
  if (run.status !== "failed" || run.retry_at === null) {
    return [];
  }
  const attempt = `${run.auto_retries + 1} of ${run.retry_policy.auto_retry_count}`;
  const detail = `Attempt ${attempt} starts at ${formatDateTime(run.retry_at)}, from the stage that failed.`;
  return [{ key: "retry-pending", tone: "info", title: "Retrying automatically", detail }];
}

function fromLog(log: RunLog, index: number): AutomaticEvent | null {
  const key = `log-${index}`;
  if (log.stage_id !== null) {
    return null;
  }
  if (log.message.startsWith(AUTO_RETRY_PREFIX)) {
    return { key, tone: "info", title: "Retried automatically", detail: log.message };
  }
  if (skippedStartTime(log.message) !== null) {
    return { key, tone: "warning", title: "Scheduled start skipped", detail: log.message };
  }
  if (log.message.startsWith(AUTO_PUBLISH_STOPPED_PREFIX)) {
    return { key, tone: "warning", title: "Auto-publish stopped", detail: log.message };
  }
  return null;
}

export function automaticEvents(run: Run): AutomaticEvent[] {
  const logged = run.logs.map(fromLog).filter((event): event is AutomaticEvent => event !== null);
  return [...rejection(run), ...pendingRetry(run), ...logged];
}
