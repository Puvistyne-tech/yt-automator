import { SETTINGS } from "@/api/mocks/fixtures/settings";
import type { AppSettings } from "@/api/types";
import { LOG_LEVEL_OPTIONS, settingNote } from "@/features/app-settings/fieldText";
import { settingsChanged, settingsInput, validateSettings } from "@/features/app-settings/validate";

const settings: AppSettings = { ...structuredClone(SETTINGS), locked: {} };

describe("app settings input", () => {
  it("drops the read-only fields", () => {
    expect(settingsInput(settings)).toEqual({
      timezone: "Asia/Kolkata",
      max_parallel_runs: 1,
      keep_runs_days: 30,
      keep_intermediate_days: 0,
      auto_cleanup_enabled: false,
      cleanup_interval_hours: 24,
      caption_track_name: "English",
      max_run_log_entries: 2000,
      log_level: "info",
      doctor_min_free_gb: 10,
    });
  });

  it("is unchanged until a field differs", () => {
    expect(settingsChanged(settingsInput(settings), settings)).toBe(false);
    expect(settingsChanged({ ...settingsInput(settings), keep_runs_days: 7 }, settings)).toBe(true);
  });
});

describe("validateSettings", () => {
  it.each([
    [{ timezone: "" }, { timezone: "Choose a timezone." }],
    [{ max_parallel_runs: 0 }, { max_parallel_runs: "Use a whole number, at least 1." }],
    [{ keep_runs_days: 1.5 }, { keep_runs_days: "Use a whole number of days, 0 or more." }],
    [{ keep_runs_days: 0 }, {}],
    [
      { keep_intermediate_days: Number.NaN },
      { keep_intermediate_days: "Use a whole number of days, 0 or more." },
    ],
    [
      { cleanup_interval_hours: -2 },
      { cleanup_interval_hours: "Use a whole number of hours, 0 or more." },
    ],
    [{ cleanup_interval_hours: 0 }, {}],
    [{ max_run_log_entries: 0 }, { max_run_log_entries: "Use a whole number, at least 1." }],
    [{ doctor_min_free_gb: -0.5 }, { doctor_min_free_gb: "Use a number, 0 or more." }],
    [{ doctor_min_free_gb: Number.NaN }, { doctor_min_free_gb: "Use a number, 0 or more." }],
    [{ doctor_min_free_gb: 2.5 }, {}],
    [{}, {}],
  ])("validates %j", (patch, errors) => {
    expect(validateSettings({ ...settingsInput(settings), ...patch })).toEqual(errors);
  });

  it("skips fields the environment locks", () => {
    const input = { ...settingsInput(settings), max_run_log_entries: 0 };
    expect(validateSettings(input, { max_run_log_entries: "Set by AUTOMATOR_X" })).toEqual({});
  });
});

describe("setting notes", () => {
  it("reports a lock reason and the restart marker from the API", () => {
    const locked = { ...settings, locked: { log_level: "Set by AUTOMATOR_LOG_LEVEL" } };
    expect(settingNote(locked, "log_level")).toEqual({
      locked: "Set by AUTOMATOR_LOG_LEVEL",
      restart: true,
    });
    expect(settingNote(locked, "timezone")).toEqual({ locked: undefined, restart: false });
  });

  it("titles every log level", () => {
    expect(LOG_LEVEL_OPTIONS.map((option) => option.label)).toEqual([
      "Debug",
      "Info",
      "Warning",
      "Error",
      "Critical",
    ]);
  });
});
