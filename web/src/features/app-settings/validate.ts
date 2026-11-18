import type { FieldErrors } from "@/api/errors";
import { settingsInput } from "@/api/settingsFields";
import type { AppSettingName, AppSettings, AppSettingsInput } from "@/api/types";
import { isIntegerAtLeast } from "@/shared/format/numbers";

export { settingsInput };

const WHOLE_NUMBERS: [AppSettingName, number, string][] = [
  ["max_parallel_runs", 1, "Use a whole number, at least 1."],
  ["keep_runs_days", 0, "Use a whole number of days, 0 or more."],
  ["keep_intermediate_days", 0, "Use a whole number of days, 0 or more."],
  ["cleanup_interval_hours", 0, "Use a whole number of hours, 0 or more."],
  ["max_run_log_entries", 1, "Use a whole number, at least 1."],
];

function numberValue(input: AppSettingsInput, name: AppSettingName): number | null {
  const value = input[name];
  return typeof value === "number" ? value : null;
}

export function validateSettings(
  input: AppSettingsInput,
  locked: AppSettings["locked"] = {},
): FieldErrors {
  const errors: FieldErrors = {};
  if (input.timezone.trim() === "") {
    errors.timezone = "Choose a timezone.";
  }
  for (const [name, minimum, message] of WHOLE_NUMBERS) {
    if (!isIntegerAtLeast(numberValue(input, name), minimum)) {
      errors[name] = message;
    }
  }
  if (!(input.doctor_min_free_gb >= 0)) {
    errors.doctor_min_free_gb = "Use a number, 0 or more.";
  }
  return Object.fromEntries(Object.entries(errors).filter(([name]) => !(name in locked)));
}

export function settingsChanged(input: AppSettingsInput, settings: AppSettings): boolean {
  return JSON.stringify(input) !== JSON.stringify(settingsInput(settings));
}
