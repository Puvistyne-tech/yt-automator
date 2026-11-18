import {
  cardGroups,
  cardOption,
  filteredCards,
  groupLabels,
  offersSearch,
  SEARCH_FROM,
  selectedLabel,
} from "@/shared/schema-form/cardOptions";

const options = [
  cardOption({
    value: "a",
    label: "Apple",
    schema: { description: "Crisp fruit", "x-group": "Fruit", "x-swatches": ["#ff0000", 3] },
  }),
  cardOption({ value: "b", label: "Basil", schema: { "x-group": "Herb" } }),
  cardOption({ value: "c", label: "Cherry", schema: { "x-group": "Fruit", "x-swatches": "red" } }),
  cardOption({ value: 4, label: "Plain", schema: null }),
  cardOption({ value: "e", label: "Empty", schema: { "x-group": "", description: 7 } }),
];

describe("card options", () => {
  it("reads description, group and only hex swatches from each entry", () => {
    expect(options[0]).toEqual({
      value: "a",
      label: "Apple",
      description: "Crisp fruit",
      group: "Fruit",
      swatches: ["#ff0000"],
    });
    expect(options[2]?.swatches).toEqual([]);
    expect(options[3]).toMatchObject({ description: "", group: null, swatches: [] });
    expect(options[4]).toMatchObject({ description: "", group: null });
  });

  it("lists group labels once in order and groups options by first appearance", () => {
    expect(groupLabels(options)).toEqual(["Fruit", "Herb"]);
    expect(cardGroups(options).map((group) => [group.label, group.options.length])).toEqual([
      ["Fruit", 2],
      ["Herb", 1],
      [null, 2],
    ]);
  });

  it.each([
    ["", null, ["Apple", "Basil", "Cherry", "Plain", "Empty"]],
    ["", "Fruit", ["Apple", "Cherry"]],
    ["CRISP", null, ["Apple"]],
    ["fruit ch", null, ["Cherry"]],
    ["herb", "Fruit", []],
  ])("filters %s within group %s", (query, group, expected) => {
    expect(filteredCards(options, query, group).map((option) => option.label)).toEqual(expected);
  });

  it("offers search only for long lists", () => {
    expect(offersSearch(SEARCH_FROM - 1)).toBe(false);
    expect(offersSearch(SEARCH_FROM)).toBe(true);
  });

  it("names the selected option and nothing for an unknown value", () => {
    expect(selectedLabel(options, "4")).toBe("Plain");
    expect(selectedLabel(options, "zzz")).toBeNull();
  });
});
