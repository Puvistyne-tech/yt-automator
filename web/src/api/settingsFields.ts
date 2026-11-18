import type { AppSettingName, AppSettings, AppSettingsInput } from "@/api/types";

export const SETTING_MINIMUMS: Partial<Record<AppSettingName, number>> = {
  max_parallel_runs: 1,
  keep_runs_days: 0,
  keep_intermediate_days: 0,
  cleanup_interval_hours: 0,
  max_run_log_entries: 1,
};

export function settingsInput(settings: AppSettingsInput | AppSettings): AppSettingsInput {
  return {
    timezone: settings.timezone,
    max_parallel_runs: settings.max_parallel_runs,
    keep_runs_days: settings.keep_runs_days,
    keep_intermediate_days: settings.keep_intermediate_days,
    auto_cleanup_enabled: settings.auto_cleanup_enabled,
    cleanup_interval_hours: settings.cleanup_interval_hours,
    caption_track_name: settings.caption_track_name,
    max_run_log_entries: settings.max_run_log_entries,
    log_level: settings.log_level,
    doctor_min_free_gb: settings.doctor_min_free_gb,
  };
}
