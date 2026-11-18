import type { FieldErrors } from "@/api/errors";
import type { AppSettings, AppSettingsInput } from "@/api/types";

export function settingsInput(settings: AppSettings): AppSettingsInput {
  return {
    timezone: settings.timezone,
    max_parallel_runs: settings.max_parallel_runs,
    keep_runs_days: settings.keep_runs_days,
  };
}

function atLeastOne(value: number): boolean {
  return Number.isInteger(value) && value >= 1;
}

export function validateSettings(input: AppSettingsInput): FieldErrors {
  const errors: FieldErrors = {};
  if (input.timezone.trim() === "") {
    errors.timezone = "Choose a timezone.";
  }
  if (!atLeastOne(input.max_parallel_runs)) {
    errors.max_parallel_runs = "Use a whole number, at least 1.";
  }
  if (!atLeastOne(input.keep_runs_days)) {
    errors.keep_runs_days = "Keep runs for at least 1 day.";
  }
  return errors;
}
