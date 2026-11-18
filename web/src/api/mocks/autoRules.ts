import {
  AUTO_PUBLISH_STARTED,
  AUTO_PUBLISH_STOPPED_PREFIX,
  autoRejectMessage,
} from "@/api/automaticEvents";
import { db } from "@/api/mocks/db";
import { publishRun } from "@/api/mocks/publish";
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

export function afterApproval(run: Run): Run {
  if (run.status !== "approved" || !run.review_policy.auto_publish) {
    return run;
  }
  if (!hasTargets(run)) {
    const reason = `${AUTO_PUBLISH_STOPPED_PREFIX} run ${run.id} has no publishable target`;
    return withLog(run, reason, "warning");
  }
  return publishRun(withLog(run, AUTO_PUBLISH_STARTED));
}
