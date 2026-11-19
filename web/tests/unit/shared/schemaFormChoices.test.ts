import {
  choiceOptions,
  choiceTitle,
  defaultChoice,
  unlistedValue,
} from "@/shared/schema-form/choices";

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

const formats = {
  type: "object",
  properties: {
    structure: {
      default: "list",
      oneOf: [
        { const: "story", title: "Story" },
        { const: "list", title: "List" },
        { const: "quiz" },
        "not a choice",
      ],
    },
    plain: { oneOf: [{ const: "a", title: "A" }] },
    free: { type: "string" },
  },
};

describe("schema choices", () => {
  it("lists a property's choices, titled by their value when untitled", () => {
    expect(choiceOptions(formats, "structure")).toEqual([
      { value: "story", title: "Story" },
      { value: "list", title: "List" },
      { value: "quiz", title: "quiz" },
    ]);
    expect(choiceOptions(formats, "free")).toEqual([]);
    expect(choiceOptions({}, "structure")).toEqual([]);
  });

  it.each([
    ["structure", "list"],
    ["plain", "a"],
    ["free", null],
    ["missing", null],
  ])("defaults %s to %j", (property, value) => {
    expect(defaultChoice(formats, property)).toBe(value);
  });

  it.each([
    ["story", "Story"],
    ["quiz", "quiz"],
    ["unknown", null],
    [null, null],
  ])("titles %j as %j", (value, title) => {
    expect(choiceTitle(formats, "structure", value)).toBe(title);
  });
});
