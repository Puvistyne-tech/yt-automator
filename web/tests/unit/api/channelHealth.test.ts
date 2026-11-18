import { channelsNeedingReconnect, needsReconnect } from "@/api/channelHealth";
import { makeChannel } from "@/api/mocks/fixtures/factories";

describe("needsReconnect", () => {
  it.each([
    ["connected", false],
    ["expired", true],
    ["revoked", true],
  ] as const)("is %s for a %s channel", (status, expected) => {
    expect(needsReconnect(makeChannel({ status }))).toBe(expected);
  });
});

describe("channelsNeedingReconnect", () => {
  const channels = [
    makeChannel({ id: "ok" }),
    makeChannel({ id: "old", status: "expired" }),
    makeChannel({ id: "gone", status: "revoked" }),
  ];

  it("lists each targeted channel that needs reconnecting once", () => {
    const found = channelsNeedingReconnect(["old", "ok", "old", "gone", "missing"], channels);
    expect(found.map((channel) => channel.id)).toEqual(["old", "gone"]);
  });

  it("returns nothing when every targeted channel is connected", () => {
    expect(channelsNeedingReconnect(["ok"], channels)).toEqual([]);
  });
});
