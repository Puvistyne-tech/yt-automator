import { cronError, describeCron } from "@/shared/format/cron";

describe("cronError", () => {
  it.each([
    "0 18 * * *",
    "*/15 * * * *",
    "0 */6 * * *",
    "30 9 * * 1-5",
    "0 8 1 JAN *",
    "0 8 * * MON,WED,FRI",
    "0 0 * * 7",
  ])("accepts %s", (expression) => {
    expect(cronError(expression)).toBeNull();
  });

  it.each([
    ["", "A cron expression needs exactly 5 fields: minute hour day month weekday."],
    ["0 18 * *", "A cron expression needs exactly 5 fields: minute hour day month weekday."],
    ["60 18 * * *", 'The minute field "60" is not valid.'],
    ["0 24 * * *", 'The hour field "24" is not valid.'],
    ["0 0 0 * *", 'The day of month field "0" is not valid.'],
    ["0 0 * 13 *", 'The month field "13" is not valid.'],
    ["0 0 * * 8", 'The day of week field "8" is not valid.'],
    ["*/0 * * * *", 'The minute field "*/0" is not valid.'],
    ["0 5-2 * * *", 'The hour field "5-2" is not valid.'],
    ["x * * * *", 'The minute field "x" is not valid.'],
  ])("rejects %j", (expression, message) => {
    expect(cronError(expression)).toBe(message);
  });
});

describe("describeCron", () => {
  it.each([
    ["0 18 * * *", "Every day at 18:00"],
    ["5 7 * * 1-5", "Every weekday at 07:05"],
    ["0 9 * * 1,3", "Every Monday, Wednesday at 09:00"],
    ["0 9 15 * *", "On day 15 of every month at 09:00"],
    ["* * * * *", "Every minute"],
    ["*/10 * * * *", "Every 10 minutes"],
    ["0 */6 * * *", "Every 6 hours"],
    ["15 */2 * * *", "Every 2 hours at minute 15"],
    ["30 * * * *", "Every hour at minute 30"],
    ["0 9 * 1 *", "Custom schedule (0 9 * 1 *)"],
    ["0 9 * * MON,WED", "Custom schedule (0 9 * * MON,WED)"],
    ["0 9 * * 0", "Every Sunday at 09:00"],
    ["0 9 * * 7", "Every Sunday at 09:00"],
    ["nonsense", "Invalid cron expression"],
  ])("describes %s as %s", (expression, text) => {
    expect(describeCron(expression)).toBe(text);
  });
});
