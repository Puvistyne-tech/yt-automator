const TIME_OF_DAY = /^([01]\d|2[0-3]):[0-5]\d$/;
const NOT_PUBLIC_PRIVACIES: readonly (string | null)[] = ["private", "unlisted"];
const MINUTES_PER_HOUR = 60;

export function isTimeOfDay(value: string | null): value is string {
  return value !== null && TIME_OF_DAY.test(value);
}

export function isNotPublic(privacy: string | null): boolean {
  return NOT_PUBLIC_PRIVACIES.includes(privacy);
}

export function minutesOfDay(value: string): number {
  const [hours = 0, minutes = 0] = value.split(":").map(Number);
  return hours * MINUTES_PER_HOUR + minutes;
}

export function withinHours(minute: number, start: number, end: number): boolean {
  return start <= end ? minute >= start && minute < end : minute >= start || minute < end;
}
