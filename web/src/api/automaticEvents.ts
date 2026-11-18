export const AUTO_REJECT_PREFIX = "Rejected automatically:";
export const AUTO_RETRY_PREFIX = "Automatic retry ";
export const AUTO_PUBLISH_STARTED = "Publishing automatically after approval";
export const AUTO_PUBLISH_STOPPED_PREFIX = "Auto-publish stopped:";
const SKIPPED_START = /^Scheduled start at (.+) skipped: /;

export function autoRejectMessage(score: number, threshold: number): string {
  return `${AUTO_REJECT_PREFIX} the score ${score.toFixed(1)} is below the auto-reject threshold ${threshold}`;
}

export function autoRetryMessage(
  attempt: number,
  count: number,
  stageId: string,
  error: string,
): string {
  return `${AUTO_RETRY_PREFIX}${attempt} of ${count} from stage ${stageId} after: ${error}`;
}

export function skippedStartMessage(when: string, runId: string, state: string): string {
  return `Scheduled start at ${when} skipped: run ${runId} is still ${state}`;
}

export function skippedStartTime(message: string): string | null {
  return SKIPPED_START.exec(message)?.[1] ?? null;
}
