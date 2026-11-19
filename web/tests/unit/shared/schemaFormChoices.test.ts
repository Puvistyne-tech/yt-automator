import { unlistedValue } from "@/shared/schema-form/choices";

const options = [
  { value: "", label: "Default" },
  { value: "kayal", label: "Kayal" },
];

describe("unlistedValue", () => {
  it("returns a stored string that no option offers", () => {
    expect(unlistedValue("my_voice", options)).toBe("my_voice");
  });

  it.each([["kayal"], [""], [undefined], [null], [7]])("returns nothing for %j", (value) => {
    expect(unlistedValue(value, options)).toBeNull();
  });
});
