import type { FieldErrors } from "@/api/errors";
import { SETTING_MINIMUMS, settingsInput } from "@/api/settingsFields";
import type { AppSettingName, AppSettings, AppSettingsInput } from "@/api/types";
import { isIntegerAtLeast } from "@/shared/format/numbers";

export { settingsInput };

function unitText(name: AppSettingName): string {
  if (name.endsWith("_days")) {
    return " of days";
  }
  return name.endsWith("_hours") ? " of hours" : "";
}

export function minimumMessage(name: AppSettingName, minimum: number): string {
  const bound = minimum === 0 ? "0 or more" : `at least ${minimum}`;
  return `Use a whole number${unitText(name)}, ${bound}.`;
}

const WHOLE_NUMBERS = Object.entries(SETTING_MINIMUMS) as [AppSettingName, number][];

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
  for (const [name, minimum] of WHOLE_NUMBERS) {
    if (!isIntegerAtLeast(numberValue(input, name), minimum)) {
      errors[name] = minimumMessage(name, minimum);
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
