import type { JsonObject } from "@/api/types/common";
import type { RunStatus, RunSummary } from "@/api/types/runs";

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
  unavailable_reason: string;
  placeholder: boolean;
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

export const SERVER_LOG_LEVELS = ["debug", "info", "warning", "error", "critical"] as const;

export type ServerLogLevel = (typeof SERVER_LOG_LEVELS)[number];

export interface AppSettingsInput {
  timezone: string;
  max_parallel_runs: number;
  keep_runs_days: number;
  keep_intermediate_days: number;
  auto_cleanup_enabled: boolean;
  cleanup_interval_hours: number;
  caption_track_name: string;
  max_run_log_entries: number;
  log_level: ServerLogLevel;
  doctor_min_free_gb: number;
}

export type AppSettingName = keyof AppSettingsInput;

export interface AppSettings extends AppSettingsInput {
  data_dir: string;
  locked: Partial<Record<AppSettingName, string>>;
  restart_required: AppSettingName[];
}

export interface AutomationUsage {
  automation_id: string;
  automation_name: string;
  runs: number;
  final_bytes: number;
  intermediate_bytes: number;
}

export interface StorageReport {
  data_dir: string;
  data_dir_bytes: number;
  free_bytes: number | null;
  disk_bytes: number | null;
  final_bytes: number;
  intermediate_bytes: number;
  orphan_bytes: number;
  other_bytes: number;
  automations: AutomationUsage[];
}

export type CleanupAction = "delete_run" | "remove_intermediate" | "remove_orphan";

export interface CleanupItem {
  run_id: string;
  action: CleanupAction;
  automation_id: string | null;
  automation_name: string;
  status: RunStatus | null;
  finished_at: string | null;
  bytes: number;
}

export interface CleanupReport {
  dry_run: boolean;
  keep_runs_days: number;
  keep_intermediate_days: number;
  items: CleanupItem[];
  total_bytes: number;
}

export interface Health {
  status: string;
  version: string;
}
