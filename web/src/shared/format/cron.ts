interface FieldSpec {
  name: string;
  min: number;
  max: number;
  names?: string[];
}

const FIELDS: FieldSpec[] = [
  { name: "minute", min: 0, max: 59 },
  { name: "hour", min: 0, max: 23 },
  { name: "day of month", min: 1, max: 31 },
  {
    name: "month",
    min: 1,
    max: 12,
    names: ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
  },
  { name: "day of week", min: 0, max: 7, names: ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"] },
];

const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

function toNumber(token: string, spec: FieldSpec): number | null {
  const named = spec.names?.indexOf(token.toUpperCase()) ?? -1;
  if (named >= 0) {
    return named + (spec.min === 1 ? 1 : 0);
  }
  return /^\d+$/.test(token) ? Number(token) : null;
}

function validRange(range: string, spec: FieldSpec): boolean {
  if (range === "*") {
    return true;
  }
  const bounds = range.split("-").map((token) => toNumber(token, spec));
  if (bounds.length > 2 || bounds.some((v) => v === null || v < spec.min || v > spec.max)) {
    return false;
  }
  const [low, high] = bounds as number[];
  return high === undefined || (low ?? 0) <= high;
}

function validPart(part: string, spec: FieldSpec): boolean {
  const [range = "", step, ...extra] = part.split("/");
  if (extra.length > 0 || (step !== undefined && !/^[1-9]\d*$/.test(step))) {
    return false;
  }
  return validRange(range, spec);
}

export function cronError(expression: string): string | null {
  const fields = expression.trim().split(/\s+/).filter(Boolean);
  if (fields.length !== 5) {
    return "A cron expression needs exactly 5 fields: minute hour day month weekday.";
  }
  const bad = fields.findIndex((field, i) => {
    const spec = FIELDS[i] as FieldSpec;
    return !field.split(",").every((part) => validPart(part, spec));
  });
  return bad === -1 ? null : `The ${FIELDS[bad]?.name} field "${fields[bad]}" is not valid.`;
}

const isNumber = (value: string) => /^\d+$/.test(value);
const pad = (value: string) => value.padStart(2, "0");

function weekdays(field: string): string | null {
  if (field === "1-5") {
    return "weekday";
  }
  const days = field.split(",");
  if (!days.every(isNumber)) {
    return null;
  }
  return days.map((d) => DAY_NAMES[Number(d)] ?? d).join(", ");
}

function describeDaily(minute: string, hour: string, dom: string, month: string, dow: string) {
  const time = `${pad(hour)}:${pad(minute)}`;
  if (dom === "*" && month === "*" && dow === "*") {
    return `Every day at ${time}`;
  }
  if (dom === "*" && month === "*") {
    const days = weekdays(dow);
    return days === null ? null : `Every ${days} at ${time}`;
  }
  if (isNumber(dom) && month === "*" && dow === "*") {
    return `On day ${dom} of every month at ${time}`;
  }
  return null;
}

function describeFrequent(minute: string, hour: string): string | null {
  if (minute === "*" && hour === "*") {
    return "Every minute";
  }
  const minuteStep = /^\*\/(\d+)$/.exec(minute);
  if (minuteStep && hour === "*") {
    return `Every ${minuteStep[1]} minutes`;
  }
  const hourStep = /^\*\/(\d+)$/.exec(hour);
  if (hourStep && isNumber(minute)) {
    return minute === "0"
      ? `Every ${hourStep[1]} hours`
      : `Every ${hourStep[1]} hours at minute ${minute}`;
  }
  return isNumber(minute) && hour === "*" ? `Every hour at minute ${minute}` : null;
}

export function describeCron(expression: string): string {
  if (cronError(expression) !== null) {
    return "Invalid cron expression";
  }
  const [minute = "", hour = "", dom = "", month = "", dow = ""] = expression.trim().split(/\s+/);
  const rest = dom === "*" && month === "*" && dow === "*";
  const daily =
    isNumber(minute) && isNumber(hour) ? describeDaily(minute, hour, dom, month, dow) : null;
  const frequent = rest ? describeFrequent(minute, hour) : null;
  return daily ?? frequent ?? `Custom schedule (${expression.trim()})`;
}
