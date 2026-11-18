import { positiveNumberOption } from "@/shared/schema-form/options";

describe("positiveNumberOption", () => {
  it.each([
    [{ rows: 3 }, "rows", 3],
    [{ step: 0.05 }, "step", 0.05],
    [{ rows: "3" }, "rows", undefined],
    [{ step: Number.NaN }, "step", undefined],
    [{ step: Number.POSITIVE_INFINITY }, "step", undefined],
    [{ step: Number.NEGATIVE_INFINITY }, "step", undefined],
    [{ step: 0 }, "step", undefined],
    [{ step: -1 }, "step", undefined],
    [{ step: null }, "step", undefined],
    [{ step: undefined }, "step", undefined],
    [{}, "rows", undefined],
  ])("reads %o %s as %s", (options, key, expected) => {
    expect(positiveNumberOption(options, key)).toBe(expected);
  });
});
