export type JsonObject = Record<string, unknown>;

export type Privacy = "private" | "unlisted" | "public";
export type ChannelStatus = "connected" | "expired" | "revoked";
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
export type ScheduleKind = "manual" | "interval" | "cron";
export type ReviewMode = "always" | "auto_when_score_at_least";
export type Aspect = "16:9" | "9:16";

export interface Credential {
  id: string;
  name: string;
  client_id: string;
  daily_quota_units: number;
  created_at: string;
}

export interface CredentialSummary extends Credential {
  has_secret: boolean;
  quota_used_today: number;
}

export interface CredentialInput {
  name: string;
  client_id: string;
  client_secret: string;
  daily_quota_units?: number;
}

export type CredentialPatch = Partial<CredentialInput>;

export interface ChannelDefaults {
  privacy: Privacy;
  made_for_kids: boolean;
  category_id: string;
  default_language: string;
  notify_subscribers: boolean;
}

export interface Channel {
  id: string;
  credential_id: string;
  youtube_channel_id: string;
  title: string;
  thumbnail_url: string;
  status: ChannelStatus;
  defaults: ChannelDefaults;
  connected_at: string;
}

export interface Playlist {
  id: string;
  title: string;
}

export interface StageDescriptor {
  id: string;
  title: string;
  description: string;
}

export interface LanguageOption {
  code: string;
  name: string;
}

export interface VariantOption {
  id: string;
  name: string;
  aspect: Aspect;
  description: string;
}

export interface PipelineDescriptor {
  type_id: string;
  name: string;
  description: string;
  version: string;
  settings_schema: JsonObject;
  default_settings: JsonObject;
  ui_schema: JsonObject;
  stages: StageDescriptor[];
  languages: LanguageOption[];
  variants: VariantOption[];
  capabilities: string[];
}

export interface Target {
  id: string;
  channel_id: string;
  language: string;
  variants: string[];
  privacy: Privacy | null;
  made_for_kids: boolean | null;
  playlist_id: string | null;
  publish_delay_minutes: number;
}

export type TargetInput = Omit<Target, "id"> & { id?: string };

export interface Schedule {
  kind: ScheduleKind;
  every_hours: number | null;
  cron: string | null;
  timezone: string;
}

export interface ReviewPolicy {
  mode: ReviewMode;
  min_score: number;
}

export interface RunSummary {
  id: string;
  status: RunStatus;
  score: number | null;
  created_at: string;
  finished_at: string | null;
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
  enabled: boolean;
}

export interface StageRun {
  stage_id: string;
  title: string;
  status: StageStatus;
  provider: string | null;
  message: string | null;
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
  decision: "approved" | "rejected";
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
  stages: StageRun[];
  artifacts: Artifact[];
  score: number | null;
  score_details: ScoreItem[];
  review: Review | null;
  uploads: Upload[];
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

export interface LogLine {
  at: string;
  message: string;
  level: string;
  stage_id: string | null;
}

export interface DashboardRun extends RunSummary {
  automation_name: string;
}

export interface QuotaUsage {
  credential_id: string;
  name: string;
  used: number;
  limit: number;
}

export interface Dashboard {
  automations: number;
  enabled_automations: number;
  channels: number;
  runs_awaiting_review: number;
  runs_today: number;
  recent_runs: DashboardRun[];
  quota: QuotaUsage[];
}

export interface ProviderChoice {
  provider_id: string;
  enabled: boolean;
  options: JsonObject;
}

export interface ProviderConfig {
  capability: string;
  chain: ProviderChoice[];
}

export interface ProviderDescriptor {
  provider_id: string;
  capability: string;
  name: string;
  description: string;
  options_schema: JsonObject;
  required_secrets: string[];
  offline: boolean;
  available: boolean;
  unavailable_reason: string | null;
}

export interface ProvidersResponse {
  descriptors: ProviderDescriptor[];
  config: ProviderConfig[];
}

export interface SecretInfo {
  name: string;
  title: string;
  description: string;
  is_set: boolean;
}

export interface AppSettings {
  timezone: string;
  max_parallel_runs: number;
  keep_runs_days: number;
  data_dir: string;
}

export type AppSettingsInput = Omit<AppSettings, "data_dir">;

export interface RunFilters {
  automation_id?: string;
  status?: RunStatus;
  limit?: number;
}

export interface Health {
  status: string;
  version: string;
}
