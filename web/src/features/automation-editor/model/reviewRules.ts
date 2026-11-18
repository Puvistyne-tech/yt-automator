import type { ReviewPolicy } from "@/api/types";

export const DEFAULT_REJECT_BELOW = 50;
export const REJECT_GAP = 10;

export function defaultRejectBelow(policy: ReviewPolicy): number {
  const auto = policy.mode === "auto_when_score_at_least";
  if (!auto || policy.min_score > DEFAULT_REJECT_BELOW) {
    return DEFAULT_REJECT_BELOW;
  }
  return Math.max(0, policy.min_score - REJECT_GAP);
}

export function withRejectBelow(policy: ReviewPolicy, enabled: boolean): ReviewPolicy {
  return { ...policy, reject_below: enabled ? defaultRejectBelow(policy) : null };
}
