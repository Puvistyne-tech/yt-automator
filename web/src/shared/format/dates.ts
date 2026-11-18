const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

export function formatDateTime(iso: string | null | undefined, timeZone?: string): string {
  if (!iso) {
    return "—";
  }
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    ...(timeZone === undefined ? {} : { timeZone }),
  }).format(new Date(iso));
}

function unitFor(abs: number): [Intl.RelativeTimeFormatUnit, number] {
  if (abs < HOUR) {
    return ["minute", MINUTE];
  }
  if (abs < DAY) {
    return ["hour", HOUR];
  }
  return ["day", DAY];
}

export function formatRelative(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) {
    return "—";
  }
  const diff = new Date(iso).getTime() - now.getTime();
  const abs = Math.abs(diff);
  if (abs < MINUTE) {
    return diff >= 0 ? "in less than a minute" : "just now";
  }
  const [unit, size] = unitFor(abs);
  return new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(
    Math.round(diff / size),
    unit,
  );
}

export function formatDuration(
  start: string | null | undefined,
  end: string | null | undefined,
  now: Date = new Date(),
): string {
  if (!start) {
    return "—";
  }
  const ms = Math.max(0, (end ? new Date(end) : now).getTime() - new Date(start).getTime());
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
