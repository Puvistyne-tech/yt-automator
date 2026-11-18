import { describe, expect, it } from "vitest";
import {
  changedCount,
  defaultPreview,
  isChanged,
  resetField,
  resetFields,
  sameSettingValue,
  tracksChanges,
  valueAt,
  withValueAt,
} from "@/shared/schema-form/defaults";

const defaults = {
  name: { en: "Story Time", ta: "கதை நேரம்" },
  minutes: 5,
  tags: ["kindness", "sharing"],
  cast: [{ name: "Kavin" }],
  style: "watercolour",
  extra: null,
};

describe("valueAt and withValueAt", () => {
  it("reads nested values and missing paths", () => {
    expect(valueAt(defaults, ["name", "ta"])).toBe("கதை நேரம்");
    expect(valueAt(defaults, ["cast", 0, "name"])).toBe("Kavin");
    expect(valueAt(defaults, ["name", "fr", "x"])).toBeUndefined();
    expect(valueAt(defaults, [])).toBe(defaults);
  });

  it("writes without touching the source", () => {
    const next = withValueAt(defaults, ["name", "en"], "Bedtime");
    expect(valueAt(next, ["name", "en"])).toBe("Bedtime");
    expect(defaults.name.en).toBe("Story Time");
    expect(withValueAt({}, ["a", "b"], 1)).toEqual({ a: { b: 1 } });
    expect(withValueAt({ list: [1, 2] }, ["list", 1], 3)).toEqual({ list: [1, 3] });
    expect(withValueAt(defaults, [], 7)).toBe(7);
  });
});

describe("sameSettingValue", () => {
  it("compares deeply, ignoring key order, with null equal to missing", () => {
    expect(sameSettingValue({ a: 1, b: [1, { c: 2 }] }, { b: [1, { c: 2 }], a: 1 })).toBe(true);
    expect(sameSettingValue([1, 2], [2, 1])).toBe(false);
    expect(sameSettingValue([1], [1, 2])).toBe(false);
    expect(sameSettingValue({ a: 1 }, { a: 1, b: 2 })).toBe(false);
    expect(sameSettingValue(null, undefined)).toBe(true);
    expect(sameSettingValue({ a: null }, {})).toBe(true);
    expect(sameSettingValue("1", 1)).toBe(false);
    expect(sameSettingValue([1], { 0: 1 })).toBe(false);
  });
});

describe("change tracking", () => {
  const value = {
    ...defaults,
    name: { en: "Bedtime", ta: "கதை நேரம்" },
    tags: ["kindness"],
    cast: [{ name: "Mira" }],
    unknown: "kept",
  };

  it("tracks named paths outside array items only", () => {
    expect(tracksChanges([])).toBe(false);
    expect(tracksChanges(["cast", 0, "name"])).toBe(false);
    expect(tracksChanges(["name", "en"])).toBe(true);
  });

  it("marks changed fields and arrays, never fields without a default", () => {
    expect(isChanged(value, defaults, ["name", "en"])).toBe(true);
    expect(isChanged(value, defaults, ["name", "ta"])).toBe(false);
    expect(isChanged(value, defaults, ["tags"])).toBe(true);
    expect(isChanged(value, defaults, ["unknown"])).toBe(false);
    expect(isChanged(value, defaults, ["cast", 0, "name"])).toBe(false);
  });

  it("counts changed leaves under the named fields", () => {
    expect(changedCount(value, defaults, ["name", "minutes", "tags", "cast"])).toBe(3);
    expect(changedCount(value, defaults, ["minutes", "extra", "unknown"])).toBe(0);
    expect(changedCount({ name: "flat" }, defaults, ["name"])).toBe(1);
  });

  it("resets one field or whole sections to copies of the defaults", () => {
    const one = resetField(value, defaults, ["name", "en"]);
    expect(valueAt(one, ["name", "en"])).toBe("Story Time");
    expect(one.tags).toEqual(["kindness"]);
    const section = resetFields(value, defaults, ["tags", "cast", "unknown"]);
    expect(section.tags).toEqual(defaults.tags);
    expect(section.tags).not.toBe(defaults.tags);
    expect(section.unknown).toBe("kept");
    expect(section.name.en).toBe("Bedtime");
  });
});

describe("defaultPreview", () => {
  it("describes the default briefly", () => {
    expect(defaultPreview("Story Time")).toBe("Story Time");
    expect(defaultPreview("")).toBe("empty");
    expect(defaultPreview(null)).toBe("not set");
    expect(defaultPreview(true)).toBe("on");
    expect(defaultPreview(false)).toBe("off");
    expect(defaultPreview(0.3)).toBe("0.3");
    expect(defaultPreview(["a", "b"])).toBe("2 items");
    expect(defaultPreview([])).toBe("no items");
    expect(defaultPreview(["a"])).toBe("1 item");
    expect(defaultPreview({ a: 1 })).toBe("default values");
    expect(defaultPreview("x".repeat(80))).toBe(`${"x".repeat(47)}…`);
  });
});
