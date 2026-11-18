import { describeCron } from "@/shared/format/cron";

export interface ScheduleLike {
  kind: "manual" | "interval" | "cron";
  every_hours: number | null;
  cron: string | null;
  timezone: string;
}

export function describeInterval(hours: number | null): string {
  if (hours === null || !Number.isFinite(hours) || hours < 1) {
    return "Every — hours";
  }
  if (hours === 1) {
    return "Every hour";
  }
  if (hours % 24 === 0) {
    const days = hours / 24;
    return days === 1 ? "Every day" : `Every ${days} days`;
  }
  return `Every ${hours} hours`;
}

export function describeSchedule(schedule: ScheduleLike): string {
  switch (schedule.kind) {
    case "manual":
      return "Manual only";
    case "interval":
      return describeInterval(schedule.every_hours);
    case "cron":
      return `${describeCron(schedule.cron ?? "")} (${schedule.timezone})`;
  }
}

export function timezoneOptions(current: string): string[] {
  const zones =
    typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];
  const all = new Set(["UTC", ...zones]);
  if (current !== "") {
    all.add(current);
  }
  return [...all];
}

export function timezoneSelectOptions(current: string): { value: string; label: string }[] {
  return timezoneOptions(current).map((zone) => ({ value: zone, label: zone }));
}
