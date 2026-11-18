import { formatDateTime, formatDuration, formatRelative } from "@/shared/format/dates";
import { formatBytes, formatNumber, formatScore, isIntegerAtLeast } from "@/shared/format/numbers";
import {
  describeInterval,
  describeSchedule,
  timezoneOptions,
  timezoneSelectOptions,
} from "@/shared/format/schedule";
import { humanizeId, pluralize } from "@/shared/format/text";

const NOW = new Date("2026-03-01T12:00:00Z");
const offset = (ms: number) => new Date(NOW.getTime() + ms).toISOString();

describe("dates", () => {
  it("formats a date and time in a given zone, or a dash when missing", () => {
    expect(formatDateTime("2026-03-01T12:00:00Z", "UTC")).toBe("1 Mar 2026, 12:00");
    expect(formatDateTime(null)).toBe("—");
  });

  it.each([
    [-30_000, "just now"],
    [30_000, "in less than a minute"],
    [-5 * 60_000, "5 minutes ago"],
    [3 * 3_600_000, "in 3 hours"],
    [-2 * 86_400_000, "2 days ago"],
  ])("describes an offset of %d ms as %s", (ms, text) => {
    expect(formatRelative(offset(ms), NOW)).toBe(text);
  });

  it("returns a dash for a missing relative time", () => {
    expect(formatRelative(undefined, NOW)).toBe("—");
  });

  it.each([
    [45_000, "45s"],
    [125_000, "2m 5s"],
    [3_900_000, "1h 5m"],
  ])("formats a %d ms duration as %s", (ms, text) => {
    expect(formatDuration(NOW.toISOString(), offset(ms))).toBe(text);
  });

  it("measures an open duration up to now, and a missing start as a dash", () => {
    expect(formatDuration(offset(-10_000), null, NOW)).toBe("10s");
    expect(formatDuration(null, null, NOW)).toBe("—");
  });
});

describe("numbers", () => {
  it.each([
    [0, "0 B"],
    [999, "999 B"],
    [1_500, "1.5 KB"],
    [48_000_000, "48.0 MB"],
    [250_000_000, "250 MB"],
    [-3, "0 B"],
    [1_500_000_000, "1.5 GB"],
    [2e12, "2.0 TB"],
  ])("formats %d bytes as %s", (bytes, text) => {
    expect(formatBytes(bytes)).toBe(text);
  });

  it("formats numbers, scores, plurals and ids", () => {
    expect(formatNumber(10_000)).toBe("10,000");
    expect(formatScore(88)).toBe("88");
    expect(formatScore(87.25)).toBe("87.3");
    expect(formatScore(null)).toBe("—");
    expect(pluralize(1, "run")).toBe("1 run");
    expect(pluralize(3, "run")).toBe("3 runs");
    expect(pluralize(2, "child", "children")).toBe("2 children");
    expect(humanizeId("text_to_speech-v2")).toBe("Text to speech v2");
  });
});

describe("isIntegerAtLeast", () => {
  it.each([
    [1, 1, true],
    [0, 0, true],
    [0, 1, false],
    [1.5, 1, false],
    [Number.NaN, 0, false],
    [null, 0, false],
  ])("checks %s against minimum %s", (value, min, ok) => {
    expect(isIntegerAtLeast(value, min)).toBe(ok);
  });
});

describe("schedule", () => {
  it.each([
    [null, "Every — hours"],
    [0, "Every — hours"],
    [1, "Every hour"],
    [6, "Every 6 hours"],
    [24, "Every day"],
    [72, "Every 3 days"],
  ])("describes an interval of %s hours as %s", (hours, text) => {
    expect(describeInterval(hours)).toBe(text);
  });

  it.each([
    [{ kind: "manual", every_hours: null, cron: null, timezone: "UTC" }, "Manual only"],
    [{ kind: "interval", every_hours: 12, cron: null, timezone: "UTC" }, "Every 12 hours"],
    [
      { kind: "cron", every_hours: null, cron: "0 18 * * *", timezone: "Asia/Kolkata" },
      "Every day at 18:00 (Asia/Kolkata)",
    ],
  ] as const)("describes %j", (schedule, text) => {
    expect(describeSchedule(schedule)).toBe(text);
  });

  it("lists UTC first and keeps the current zone even when unknown", () => {
    const zones = timezoneOptions("Mars/Olympus");
    expect(zones[0]).toBe("UTC");
    expect(zones).toContain("Mars/Olympus");
    expect(new Set(zones).size).toBe(zones.length);
  });

  it("wraps zones as select options", () => {
    expect(timezoneSelectOptions("UTC")[0]).toEqual({ value: "UTC", label: "UTC" });
  });
});
