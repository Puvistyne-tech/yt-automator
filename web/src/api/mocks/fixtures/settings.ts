import type { AppSettings } from "@/api/types";

export interface StrayFolder {
  run_id: string;
  bytes: number;
}

export interface MockStorage {
  strays: StrayFolder[];
  other_bytes: number;
  free_bytes: number | null;
  disk_bytes: number | null;
}

export const SETTINGS: AppSettings = {
  timezone: "Asia/Kolkata",
  max_parallel_runs: 1,
  keep_runs_days: 30,
  keep_intermediate_days: 0,
  cleanup_interval_hours: 24,
  caption_track_name: "English",
  max_run_log_entries: 2000,
  log_level: "info",
  doctor_min_free_gb: 10,
  data_dir: "~/Library/Application Support/YouTube Automator",
  locked: {
    caption_track_name:
      "Set by the environment variable AUTOMATOR_YOUTUBE_CAPTION_TRACK_NAME; unset it to change it here",
  },
  restart_required: ["log_level"],
};

export const STORAGE: MockStorage = {
  strays: [{ run_id: "run-3f9a2c", bytes: 312_000_000 }],
  other_bytes: 41_000_000,
  free_bytes: 182_000_000_000,
  disk_bytes: 494_000_000_000,
};
