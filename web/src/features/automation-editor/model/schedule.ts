import { DEFAULT_SCHEDULE_LIMITS } from "@/api/automationDefaults";
import type { Schedule, ScheduleKind } from "@/api/types";

export const DEFAULT_INTERVAL_HOURS = 24;
export const DEFAULT_CRON = "0 18 * * *";
export const DEFAULT_ACTIVE_FROM = "08:00";
export const DEFAULT_ACTIVE_UNTIL = "20:00";
export const DEFAULT_DAILY_CAP = 2;

export function emptySchedule(timezone: string): Schedule {
  return { kind: "manual", every_hours: null, cron: null, timezone, ...DEFAULT_SCHEDULE_LIMITS };
}

export function withScheduleKind(schedule: Schedule, kind: ScheduleKind): Schedule {
  return {
    ...schedule,
    kind,
    every_hours:
      kind === "interval" ? (schedule.every_hours ?? DEFAULT_INTERVAL_HOURS) : schedule.every_hours,
    cron: kind === "cron" ? (schedule.cron ?? DEFAULT_CRON) : schedule.cron,
  };
}

export function withEveryHours(schedule: Schedule, hours: number): Schedule {
  return { ...schedule, every_hours: Number.isNaN(hours) ? null : hours };
}

export function withActiveHours(schedule: Schedule, enabled: boolean): Schedule {
  return enabled
    ? { ...schedule, active_from: DEFAULT_ACTIVE_FROM, active_until: DEFAULT_ACTIVE_UNTIL }
    : { ...schedule, active_from: null, active_until: null };
}

export function withDailyCap(schedule: Schedule, enabled: boolean): Schedule {
  return { ...schedule, max_runs_per_day: enabled ? DEFAULT_DAILY_CAP : null };
}

function blankToNull(value: string | null): string | null {
  return value === null || value.trim() === "" ? null : value.trim();
}

export function normalizeSchedule(schedule: Schedule): Schedule {
  return {
    kind: schedule.kind,
    every_hours: schedule.kind === "interval" ? schedule.every_hours : null,
    cron: schedule.kind === "cron" ? (schedule.cron ?? "").trim() : null,
    timezone: schedule.timezone,
    skip_if_unfinished: schedule.skip_if_unfinished,
    max_runs_per_day: schedule.max_runs_per_day,
    active_from: blankToNull(schedule.active_from),
    active_until: blankToNull(schedule.active_until),
  };
}
