import type { JsonObject, Privacy } from "@/api/types/common";
import type { RunSummary } from "@/api/types/runs";

export type ScheduleKind = "manual" | "interval" | "cron";
export type ReviewMode = "always" | "auto_when_score_at_least";

export interface Target {
  id: string;
  channel_id: string;
  language: string;
  variants: string[];
  privacy: Privacy | null;
  made_for_kids: boolean | null;
  playlist_id: string | null;
  publish_delay_minutes: number;
  publish_time_of_day: string | null;
  publish_timezone: string;
}

export type TargetInput = Omit<Target, "id"> & { id?: string };

export interface Schedule {
  kind: ScheduleKind;
  every_hours: number | null;
  cron: string | null;
  timezone: string;
  skip_if_unfinished: boolean;
  max_runs_per_day: number | null;
  active_from: string | null;
  active_until: string | null;
}

export interface ReviewPolicy {
  mode: ReviewMode;
  min_score: number;
  reject_below: number | null;
  auto_publish: boolean;
}

export interface RetryPolicy {
  auto_retry_count: number;
  retry_delay_minutes: number;
}

export interface Automation {
  id: string;
  name: string;
  description: string;
  pipeline_type: string;
  settings: JsonObject;
  languages: string[];
  targets: Target[];
  schedule: Schedule;
  review_policy: ReviewPolicy;
  retry_policy: RetryPolicy;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  next_run_at: string | null;
  last_run: RunSummary | null;
}

export interface AutomationInput {
  name: string;
  description: string;
  pipeline_type: string;
  settings: JsonObject;
  languages: string[];
  targets: TargetInput[];
  schedule: Schedule;
  review_policy: ReviewPolicy;
  retry_policy: RetryPolicy;
  enabled: boolean;
}
