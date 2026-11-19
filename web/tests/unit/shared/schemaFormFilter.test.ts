import { describe, expect, it } from "vitest";
import { changedCount, changedPaths } from "@/shared/schema-form/defaults";
import {
  hiddenLeafCount,
  matchingPaths,
  readBasicPaths,
  settingsFilter,
  shownBy,
  visiblePathSet,
  visibleProperties,
} from "@/shared/schema-form/fieldFilter";
import { schemaFields } from "@/shared/schema-form/schemaFields";
import { filterSchema as schema } from "../../helpers/filterSchema";

const fields = schemaFields(schema);

describe("schemaFields", () => {
  it("walks references and optional objects in order, stopping at arrays", () => {
    expect(fields.map((field) => [field.path, field.title, field.leaf])).toEqual([
      ["series", "Series", false],
      ["series.name", "Series name", false],
      ["series.name.en", "English", true],
      ["series.tagline", "Tagline", true],
      ["tone", "Tone", true],
      ["music", "Music", false],
      ["music.enabled", "Background music", true],
      ["music.volume", "Volume", true],
      ["cast", "Cast", true],
    ]);
  });

  it("treats a schema without properties as having no fields", () => {
    expect(schemaFields({ type: "string" })).toEqual([]);
  });
});

describe("readBasicPaths", () => {
  it("reads the string entries of ui:basic", () => {
    expect(readBasicPaths({ "ui:basic": ["tone", 3, "music.enabled"] })).toEqual([
      "tone",
      "music.enabled",
    ]);
  });

  it("returns null when the key is missing or not a list", () => {
    expect(readBasicPaths({})).toBeNull();
    expect(readBasicPaths({ "ui:basic": "tone" })).toBeNull();
    expect(readBasicPaths(null)).toBeNull();
  });
});

describe("shownBy", () => {
  const visible = shownBy(["series.name", "music.enabled"]);

  it("shows listed paths with their ancestors and descendants", () => {
    expect(
      ["series", "series.name", "series.name.en", "music", "music.enabled"].every(visible),
    ).toBe(true);
  });

  it("hides siblings and paths that only share a prefix", () => {
    expect(visible("series.tagline")).toBe(false);
    expect(visible("music.volume")).toBe(false);
    expect(visible("tone")).toBe(false);
    expect(shownBy(["music.en"])("music.enabled")).toBe(false);
  });
});

describe("matchingPaths", () => {
  it("matches titles and descriptions without regard to case", () => {
    expect(matchingPaths(fields, "VOLUME")).toEqual(["music.volume"]);
    expect(matchingPaths(fields, "covers")).toEqual(["series.tagline"]);
    expect(matchingPaths(fields, "  feels ")).toEqual(["tone"]);
  });

  it("matches nothing for an unknown word", () => {
    expect(matchingPaths(fields, "zebra")).toEqual([]);
  });
});

describe("settingsFilter", () => {
  const changed = ["music.volume", "tone"];

  it("filters nothing without a query or the changed-only switch", () => {
    expect(settingsFilter(fields, { query: " ", changedOnly: false, changed })).toBeUndefined();
  });

  it("keeps matches of the query", () => {
    const visible = settingsFilter(fields, { query: "music", changedOnly: false, changed });
    expect(visible?.("music.enabled")).toBe(true);
    expect(visible?.("tone")).toBe(false);
  });

  it("keeps only changed fields", () => {
    const visible = settingsFilter(fields, { query: "", changedOnly: true, changed });
    expect(visible?.("tone")).toBe(true);
    expect(visible?.("music.enabled")).toBe(false);
  });

  it("keeps fields that both match and changed", () => {
    const visible = settingsFilter(fields, { query: "music", changedOnly: true, changed });
    expect(visible?.("music.volume")).toBe(true);
    expect(visible?.("music.enabled")).toBe(false);
    expect(visible?.("tone")).toBe(false);
  });
});

describe("visiblePathSet", () => {
  it("collects the visible paths of a schema", () => {
    expect([...visiblePathSet(fields, shownBy(["music.enabled"]))]).toEqual([
      "music",
      "music.enabled",
    ]);
  });
});

describe("visibleProperties", () => {
  const properties = [{ name: "enabled" }, { name: "volume" }];
  const visible = visiblePathSet(fields, shownBy(["music.enabled"]));

  it("keeps the properties whose path is visible", () => {
    expect(visibleProperties(properties, ["music"], visible)).toEqual([{ name: "enabled" }]);
  });

  it("keeps everything without a rule or inside array items", () => {
    expect(visibleProperties(properties, ["music"], undefined)).toEqual(properties);
    expect(visibleProperties(properties, ["cast", 0], visible)).toEqual(properties);
  });

  it("keeps every entry of a visible setting with no visible path under it", () => {
    const entries = [{ name: "en" }, { name: "ta" }];
    expect(visibleProperties(entries, ["labels"], new Set(["labels"]))).toEqual(entries);
    expect(visibleProperties(entries, ["labels"], new Set(["other"]))).toEqual([]);
  });
});

describe("hiddenLeafCount", () => {
  it("counts the leaf fields a filter hides", () => {
    expect(hiddenLeafCount(fields, shownBy(["series", "tone"]))).toBe(3);
  });
});

describe("changedPaths", () => {
  const defaults = { name: { en: "Story Time", ta: "Kathai" }, minutes: 5, tags: ["a"] };

  it("lists the changed leaves that changedCount counts", () => {
    const value = { name: { en: "Bedtime", ta: "Kathai" }, minutes: 5, tags: ["b"] };
    const names = ["name", "minutes", "tags"];
    expect(changedPaths(value, defaults, names)).toEqual(["name.en", "tags"]);
    expect(changedCount(value, defaults, names)).toBe(2);
  });
});
