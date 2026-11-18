import type { AppSettings, AppSettingsInput } from "@/api/types";

export function settingsInput(settings: AppSettingsInput | AppSettings): AppSettingsInput {
  return {
    timezone: settings.timezone,
    max_parallel_runs: settings.max_parallel_runs,
    keep_runs_days: settings.keep_runs_days,
    keep_intermediate_days: settings.keep_intermediate_days,
    cleanup_interval_hours: settings.cleanup_interval_hours,
    caption_track_name: settings.caption_track_name,
    max_run_log_entries: settings.max_run_log_entries,
    log_level: settings.log_level,
    doctor_min_free_gb: settings.doctor_min_free_gb,
  };
}
