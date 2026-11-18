import { cronTimesOfDay } from "@/shared/format/cron";
import { isNotPublic, isTimeOfDay, minutesOfDay, withinHours } from "@/shared/format/timeOfDay";

describe("time of day", () => {
  it.each([
    ["08:00", true],
    ["23:59", true],
    ["24:00", false],
    ["8:00", false],
    [null, false],
  ])("reads %s as a time of day: %s", (value, valid) => {
    expect(isTimeOfDay(value)).toBe(valid);
  });

  it("converts to minutes and checks windows that may cross midnight", () => {
    expect(minutesOfDay("08:30")).toBe(510);
    expect(withinHours(480, 480, 1200)).toBe(true);
    expect(withinHours(1200, 480, 1200)).toBe(false);
    expect(withinHours(1380, 1320, 360)).toBe(true);
    expect(withinHours(300, 1320, 360)).toBe(true);
    expect(withinHours(600, 1320, 360)).toBe(false);
  });

  it.each([
    ["private", true],
    ["unlisted", true],
    ["public", false],
    [null, false],
  ] as const)("treats privacy %s as not public: %s", (privacy, notPublic) => {
    expect(isNotPublic(privacy)).toBe(notPublic);
  });
});

describe("cron times of day", () => {
  it.each([
    ["0 3 * * *", [180]],
    ["30 8-9 * * 1-5", [510, 570]],
    ["0 */12 * * *", [0, 720]],
    ["15,45 22 * * *", [1335, 1365]],
    ["0 20/2 * * *", [1200, 1320]],
  ])("lists the times %s matches", (expression, minutes) => {
    expect(cronTimesOfDay(expression)).toEqual(minutes);
  });

  it("lists nothing for an invalid expression", () => {
    expect(cronTimesOfDay("not cron")).toEqual([]);
  });
});
