import type { FieldErrors } from "@/api/errors";
import type { AppSettings, AppSettingsInput } from "@/api/types";
import { isIntegerAtLeast } from "@/shared/format/numbers";

export function settingsInput(settings: AppSettings): AppSettingsInput {
  return {
    timezone: settings.timezone,
    max_parallel_runs: settings.max_parallel_runs,
    keep_runs_days: settings.keep_runs_days,
  };
}

export function validateSettings(input: AppSettingsInput): FieldErrors {
  const errors: FieldErrors = {};
  if (input.timezone.trim() === "") {
    errors.timezone = "Choose a timezone.";
  }
  if (!isIntegerAtLeast(input.max_parallel_runs, 1)) {
    errors.max_parallel_runs = "Use a whole number, at least 1.";
  }
  if (!isIntegerAtLeast(input.keep_runs_days, 1)) {
    errors.keep_runs_days = "Keep runs for at least 1 day.";
  }
  return errors;
}

export function settingsChanged(input: AppSettingsInput, settings: AppSettings): boolean {
  return JSON.stringify(input) !== JSON.stringify(settingsInput(settings));
}
