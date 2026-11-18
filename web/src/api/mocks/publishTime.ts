import type { Privacy, Target } from "@/api/types";
import { minutesOfDay } from "@/shared/format/timeOfDay";

const MINUTE_MS = 60_000;
const DAY_MS = 1440 * MINUTE_MS;

function wallClock(instant: number, zone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    hourCycle: "h23",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
  }).formatToParts(new Date(instant));
  const part = (type: string) => Number(parts.find((p) => p.type === type)?.value ?? 0);
  return Date.UTC(part("year"), part("month") - 1, part("day"), part("hour"), part("minute"));
}

function zonedInstant(wall: number, zone: string): number {
  const guess = wall - (wallClock(wall, zone) - wall);
  return wall - (wallClock(guess, zone) - guess);
}

export function nextLocalTime(now: number, time: string, zone: string): number {
  const wallNow = wallClock(now, zone);
  const today = wallNow - (wallNow % DAY_MS) + minutesOfDay(time) * MINUTE_MS;
  const instant = zonedInstant(today, zone);
  return instant > now ? instant : zonedInstant(today + DAY_MS, zone);
}

export function scheduledPublish(
  target: Target,
  privacy: Privacy | null,
  now: Date,
): string | null {
  if (privacy !== "public") {
    return null;
  }
  const time = target.publish_time_of_day;
  if (time !== null) {
    return new Date(nextLocalTime(now.getTime(), time, target.publish_timezone)).toISOString();
  }
  const delay = target.publish_delay_minutes;
  return delay > 0 ? new Date(now.getTime() + delay * MINUTE_MS).toISOString() : null;
}
