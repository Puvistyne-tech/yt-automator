import {
  AUTO_PUBLISH_STARTED,
  autoPublishStoppedMessage,
  autoRejectMessage,
} from "@/api/automaticEvents";
import { db } from "@/api/mocks/db";
import { NO_UPLOAD_SUCCEEDED, publishRun } from "@/api/mocks/publish";
import type { LogLevel, Run, RunStatus } from "@/api/types";

function withLog(run: Run, message: string, level: LogLevel = "info"): Run {
  return { ...run, logs: [...run.logs, { at: db.now(), level, stage_id: null, message }] };
}

export function scoredStatus(run: Run, score: number): RunStatus {
  const { mode, min_score, reject_below } = run.review_policy;
  if (reject_below !== null && score < reject_below) {
    return "rejected";
  }
  return mode === "auto_when_score_at_least" && score >= min_score ? "approved" : "awaiting_review";
}

export function autoRejected(run: Run, score: number): Run {
  const threshold = run.review_policy.reject_below ?? 0;
  const notes = autoRejectMessage(score, threshold);
  const review = { decision: "rejected" as const, notes, decided_at: db.now() };
  return withLog({ ...run, status: "rejected", review }, notes, "warning");
}

function hasTargets(run: Run): boolean {
  const automation = db.state.automations.find((a) => a.id === run.automation_id);
  return (automation?.targets.length ?? 0) > 0;
}

export function publishesOnApproval(run: Run): boolean {
  return run.status === "approved" && run.review_policy.auto_publish;
}

export function queueAutoPublish(run: Run): Run {
  if (publishesOnApproval(run)) {
    db.state.publishQueue.push(run.id);
  }
  return run;
}

function stopped(run: Run, reason: string): Run {
  return withLog(run, autoPublishStoppedMessage(reason), "warning");
}

export function afterApproval(run: Run): Run {
  if (!publishesOnApproval(run)) {
    return run;
  }
  if (!hasTargets(run)) {
    return stopped(run, `run ${run.id} has no publishable target`);
  }
  const published = publishRun(withLog(run, AUTO_PUBLISH_STARTED));
  return published.status === "approved" ? stopped(published, NO_UPLOAD_SUCCEEDED) : published;
}
