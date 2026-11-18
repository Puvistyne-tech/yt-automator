import type { RetryPolicy, ReviewPolicy, Schedule } from "@/api/types";

export const DEFAULT_MIN_SCORE = 85;

export const DEFAULT_REVIEW_POLICY: ReviewPolicy = {
  mode: "always",
  min_score: DEFAULT_MIN_SCORE,
  reject_below: null,
  auto_publish: false,
};

export const DEFAULT_RETRY_POLICY: RetryPolicy = {
  auto_retry_count: 0,
  retry_delay_minutes: 10,
};

export const MAX_AUTO_RETRIES = 10;
export const MAX_RETRY_DELAY_MINUTES = 24 * 60;

export type ScheduleLimits = Pick<
  Schedule,
  "skip_if_unfinished" | "max_runs_per_day" | "active_from" | "active_until"
>;

export const DEFAULT_SCHEDULE_LIMITS: ScheduleLimits = {
  skip_if_unfinished: true,
  max_runs_per_day: null,
  active_from: null,
  active_until: null,
};

export const DEFAULT_PUBLISH_TIMEZONE = "UTC";
