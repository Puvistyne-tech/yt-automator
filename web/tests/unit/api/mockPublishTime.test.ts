import { makeTarget } from "@/api/mocks/fixtures/factories";
import { scheduledPublish } from "@/api/mocks/publishTime";

const NOW = new Date("2026-01-05T10:00:00Z");

describe("mock scheduled publishing", () => {
  it.each([
    [{}, "public", null],
    [{ publish_delay_minutes: 30 }, "public", "2026-01-05T10:30:00.000Z"],
    [{ publish_delay_minutes: 30 }, "private", null],
    [
      { publish_time_of_day: "18:00", publish_timezone: "UTC" },
      "public",
      "2026-01-05T18:00:00.000Z",
    ],
    [
      { publish_time_of_day: "08:00", publish_timezone: "UTC" },
      "public",
      "2026-01-06T08:00:00.000Z",
    ],
    [
      { publish_time_of_day: "18:00", publish_timezone: "Asia/Kolkata" },
      "public",
      "2026-01-05T12:30:00.000Z",
    ],
    [
      { publish_time_of_day: "09:00", publish_timezone: "America/New_York" },
      "public",
      "2026-01-05T14:00:00.000Z",
    ],
    [{ publish_time_of_day: "18:00", publish_timezone: "UTC" }, "unlisted", null],
  ] as const)("plans %j with privacy %s at %s", (fields, privacy, expected) => {
    expect(scheduledPublish(makeTarget(fields), privacy, NOW)).toBe(expected);
  });
});
