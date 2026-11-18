import { privacyFromValue } from "@/api/labels";

describe("privacyFromValue", () => {
  it.each([
    ["public", "public"],
    ["private", "private"],
    ["unlisted", "unlisted"],
    ["", null],
    ["bogus", null],
  ])("reads %j as %j", (value, privacy) => {
    expect(privacyFromValue(value)).toBe(privacy);
  });
});
