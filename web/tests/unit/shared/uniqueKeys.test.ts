import { withUniqueKeys } from "@/shared/uniqueKeys";

describe("withUniqueKeys", () => {
  it.each([
    [[], []],
    [
      ["a", "b"],
      ["a", "b"],
    ],
    [
      ["a", "a", "b", "a"],
      ["a", "a#2", "b", "a#3"],
    ],
  ])("keys %j as %j", (values, keys) => {
    const keyed = withUniqueKeys(values, (value) => value);
    expect(keyed.map((entry) => entry.key)).toEqual(keys);
    expect(keyed.map((entry) => entry.item)).toEqual(values);
  });
});
