import type { ReviewPolicy } from "@/api/types/automations";
import type { JsonObject, Privacy } from "@/api/types/common";

export type RunStatus =
  | "queued"
  | "running"
  | "awaiting_review"
  | "approved"
  | "rejected"
  | "publishing"
  | "published"
  | "failed"
  | "cancelled";
export type StageStatus = "pending" | "running" | "done" | "failed" | "skipped";
export type UploadStatus = "pending" | "uploading" | "done" | "failed" | "skipped";
export type ArtifactKind =
  | "video"
  | "subtitle"
  | "thumbnail"
  | "metadata"
  | "image"
  | "audio"
  | "text";
export type RunTrigger = "manual" | "schedule";
export type LogLevel = "info" | "warning" | "error";
export type ReviewDecision = "approved" | "rejected";

export interface RunSummary {
  id: string;
  status: RunStatus;
  score: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface StageRun {
  stage_id: string;
  title: string;
  status: StageStatus;
  provider: string;
  message: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface Artifact {
  id: string;
  kind: ArtifactKind;
  stage_id: string;
  language: string | null;
  variant: string | null;
  filename: string;
  media_type: string;
  size_bytes: number;
  meta: JsonObject;
}

export interface ScoreItem {
  id: string;
  title: string;
  score: number;
  weight: number;
  detail: string;
}

export interface Review {
  decision: ReviewDecision;
  notes: string;
  decided_at: string;
}

export interface Upload {
  target_id: string;
  channel_id: string;
  language: string;
  variant: string;
  status: UploadStatus;
  youtube_video_id: string | null;
  url: string | null;
  error: string | null;
  quota_units: number;
  privacy: Privacy | null;
  made_for_kids: boolean | null;
}

export interface Run {
  id: string;
  automation_id: string;
  automation_name: string;
  pipeline_type: string;
  status: RunStatus;
  trigger: RunTrigger;
  languages: string[];
  settings_snapshot: JsonObject;
  review_policy: ReviewPolicy;
  stages: StageRun[];
  artifacts: Artifact[];
  score: number | null;
  score_details: ScoreItem[];
  review: Review | null;
  uploads: Upload[];
  logs: RunLog[];
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export type RunEventKind = "status" | "stage" | "log" | "artifact" | "upload";

export interface RunEvent {
  run_id: string;
  kind: RunEventKind;
  at: string;
  payload: JsonObject;
}

export interface RunLog {
  at: string;
  level: LogLevel;
  stage_id: string | null;
  message: string;
}

export interface RunFilters {
  automation_id?: string;
  status?: RunStatus;
  limit?: number;
}
