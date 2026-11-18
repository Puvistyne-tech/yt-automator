import { channelOptionLabel, privacyFromValue } from "@/api/labels";

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
