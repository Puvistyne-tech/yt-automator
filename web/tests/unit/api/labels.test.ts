import { audienceOptions, channelOptionLabel, privacyFromValue } from "@/api/labels";

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

describe("channelOptionLabel", () => {
  it.each([
    ["connected", "Story Time"],
    ["expired", "Story Time (Token expired)"],
    ["revoked", "Story Time (Access revoked)"],
  ] as const)("labels a %s channel", (status, label) => {
    expect(channelOptionLabel({ title: "Story Time", status })).toBe(label);
  });
});

describe("audienceOptions", () => {
  it("lists every audience by its label", () => {
    expect(audienceOptions()).toEqual([
      { value: "kids", label: "For kids" },
      { value: "general", label: "General audience" },
    ]);
  });

  it("adds the descriptions when given", () => {
    const options = audienceOptions({ kids: "Small ones.", general: "Everyone else." });
    expect(options.map((option) => option.description)).toEqual(["Small ones.", "Everyone else."]);
  });
});
