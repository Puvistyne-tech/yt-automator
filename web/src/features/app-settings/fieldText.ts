import type { AppSettingName, AppSettings } from "@/api/types";
import { SERVER_LOG_LEVELS } from "@/api/types/system";
import type { SelectOption } from "@/shared/ui";

export interface SettingText {
  label: string;
  hint: string;
}

export const SETTING_TEXT: Record<AppSettingName, SettingText> = {
  timezone: {
    label: "Timezone",
    hint: "Used for dates in the app and as the default for new schedules.",
  },
  max_parallel_runs: {
    label: "Parallel runs",
    hint: "How many runs may render at the same time.",
  },
  caption_track_name: {
    label: "Caption track name",
    hint: "The name YouTube shows for uploaded captions. Leave empty for no name.",
  },
  keep_runs_days: {
    label: "Keep finished runs (days)",
    hint: "Finished runs and all their files are deleted this many days after they finish. 0 keeps them forever.",
  },
  keep_intermediate_days: {
    label: "Keep working files (days)",
    hint: "Pictures, clips and other working files are removed earlier; videos, thumbnails, captions and metadata stay. 0 keeps them.",
  },
  auto_cleanup_enabled: {
    label: "Clean up automatically",
    hint: "Off until you turn it on. When on, the cleanup deletes what the settings above allow on its own; when off, nothing is deleted until you choose Clean up now.",
  },
  cleanup_interval_hours: {
    label: "Automatic cleanup every (hours)",
    hint: "Runs waiting for review, approved or still uploading are never touched. 0 cleans up only when you ask.",
  },
  max_run_log_entries: {
    label: "Log entries kept per run",
    hint: "Older entries are dropped once a run has this many.",
  },
  fallback_reason_chars: {
    label: "Fallback reason length",
    hint: "Characters of a failed provider's error shown when a run falls back to another provider.",
  },
  log_level: {
    label: "Server log level",
    hint: "How much detail the server writes to its log.",
  },
  doctor_min_free_gb: {
    label: "Free disk space warning (GB)",
    hint: "The health check warns when the data folder's disk has less free space than this.",
  },
};

export const LOG_LEVEL_OPTIONS: SelectOption[] = SERVER_LOG_LEVELS.map((level) => ({
  value: level,
  label: level[0]?.toUpperCase() + level.slice(1),
}));

export const RESTART_NOTE = "Applies after restart";

export interface SettingNote {
  locked: string | undefined;
  restart: boolean;
}

export function settingNote(settings: AppSettings, name: AppSettingName): SettingNote {
  return { locked: settings.locked[name], restart: settings.restart_required.includes(name) };
}
