import { numberOption } from "@/shared/schema-form/options";

describe("numberOption", () => {
  it.each([
    [{ rows: 3 }, "rows", 3],
    [{ step: 0.05 }, "step", 0.05],
    [{ rows: "3" }, "rows", undefined],
    [{ step: Number.NaN }, "step", undefined],
    [{}, "rows", undefined],
  ])("reads %o %s as %s", (options, key, expected) => {
    expect(numberOption(options, key)).toBe(expected);
  });
});
