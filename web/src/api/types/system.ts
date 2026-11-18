import type { JsonObject } from "@/api/types/common";
import type { RunSummary } from "@/api/types/runs";

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

export interface Health {
  status: string;
  version: string;
}
