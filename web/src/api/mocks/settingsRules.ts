import { SETTING_MINIMUMS } from "@/api/settingsFields";
import type { AppSettingName, AppSettings, AppSettingsInput } from "@/api/types";
import { SERVER_LOG_LEVELS } from "@/api/types/system";

const LOG_LEVELS: readonly string[] = SERVER_LOG_LEVELS;

function isKnownZone(zone: string): boolean {
  try {
    return zone !== "" && new Intl.DateTimeFormat("en", { timeZone: zone }) !== null;
  } catch {
    return false;
  }
}

function numberErrors(input: AppSettingsInput): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [name, minimum] of Object.entries(SETTING_MINIMUMS)) {
    const value = input[name as AppSettingName];
    if (typeof value !== "number" || !Number.isInteger(value)) {
      errors[name] = "Input should be a valid integer";
    } else if (value < minimum) {
      errors[name] = `Input should be greater than or equal to ${minimum}`;
    }
  }
  if (!(input.doctor_min_free_gb >= 0)) {
    errors.doctor_min_free_gb = "Input should be greater than or equal to 0";
  }
  return errors;
}

function lockedErrors(input: AppSettingsInput, current: AppSettings): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const [name, reason] of Object.entries(current.locked)) {
    const field = name as AppSettingName;
    if (reason !== undefined && input[field] !== current[field]) {
      errors[field] = reason;
    }
  }
  return errors;
}

export function settingsErrors(
  input: AppSettingsInput,
  current: AppSettings,
): Record<string, string> {
  const errors = { ...numberErrors(input), ...lockedErrors(input, current) };
  if (!isKnownZone(input.timezone)) {
    errors.timezone = `unknown timezone '${input.timezone}'`;
  }
  if (!LOG_LEVELS.includes(input.log_level)) {
    errors.log_level = "Input should be 'debug', 'info', 'warning', 'error' or 'critical'";
  }
  return errors;
}
