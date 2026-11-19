import { describe, expect, it } from "vitest";
import {
  concealedBy,
  hiddenLeafCount,
  matchingPaths,
  readHiddenPaths,
  revealedFields,
  revealedPaths,
  settingsFilter,
  shownBy,
  visiblePathSet,
  withoutConcealed,
} from "@/shared/schema-form/fieldFilter";
import { schemaFields } from "@/shared/schema-form/schemaFields";
import { filterSchema } from "../../helpers/filterSchema";

const fields = schemaFields(filterSchema);

describe("readHiddenPaths", () => {
  it("reads the string entries of ui:hidden", () => {
    expect(readHiddenPaths({ "ui:hidden": ["series.tagline", 3] })).toEqual(["series.tagline"]);
  });

  it("reads nothing when the key is missing or not a list", () => {
    expect(readHiddenPaths({})).toEqual([]);
    expect(readHiddenPaths({ "ui:hidden": "tone" })).toEqual([]);
    expect(readHiddenPaths(undefined)).toEqual([]);
  });
});

describe("concealedBy", () => {
  it("conceals nothing without hidden paths", () => {
    expect(concealedBy(fields, [])).toBeUndefined();
  });

  it("conceals listed paths and their descendants, not their ancestors", () => {
    const concealed = concealedBy(fields, ["series.name"]);
    expect(["series.name", "series.name.en"].every((path) => concealed?.(path))).toBe(true);
    expect(["series", "series.tagline", "tone"].some((path) => concealed?.(path))).toBe(false);
    expect(concealedBy(fields, ["music.en"])?.("music.enabled")).toBe(false);
  });

  it("conceals a group whose every leaf is hidden", () => {
    const concealed = concealedBy(fields, ["music.enabled", "music.volume"]);
    expect(concealed?.("music")).toBe(true);
    expect(concealedBy(fields, ["music.enabled"])?.("music")).toBe(false);
  });

  it("conceals an array setting as one leaf", () => {
    const concealed = concealedBy(fields, ["cast"]);
    expect(concealed?.("cast")).toBe(true);
    expect(fields.filter((field) => concealed?.(field.path)).map((field) => field.path)).toEqual([
      "cast",
    ]);
  });

  it("hides nothing for a path that is not a setting", () => {
    const concealed = concealedBy(fields, ["nope.deeper"]);
    expect(fields.some((field) => concealed?.(field.path))).toBe(false);
  });
});

describe("hidden settings", () => {
  const concealed = concealedBy(fields, ["series.tagline", "music.volume"]);
  const shown = fields.filter((field) => !concealed?.(field.path)).map((field) => field.path);

  it("keeps the rule and the fields as they are without hidden paths", () => {
    const rule = shownBy(["tone"]);
    expect(withoutConcealed(rule, undefined)).toBe(rule);
    expect(withoutConcealed(undefined, undefined)).toBeUndefined();
    expect(revealedFields(fields, undefined)).toBe(fields);
    expect(revealedPaths(["tone"], undefined)).toEqual(["tone"]);
  });

  it("leaves hidden paths out of the whole form", () => {
    const visible = withoutConcealed(undefined, concealed);
    expect(visible === undefined ? [] : [...visiblePathSet(fields, visible)]).toEqual(shown);
  });

  it("leaves hidden paths out of a basic view", () => {
    const visible = withoutConcealed(shownBy(["series", "music"]), concealed);
    expect(visible?.("series.name.en")).toBe(true);
    expect(visible?.("series.tagline")).toBe(false);
    expect(visible?.("music.volume")).toBe(false);
  });

  it("does not count or search hidden fields", () => {
    const revealed = revealedFields(fields, concealed);
    expect(hiddenLeafCount(revealed, shownBy(["tone"]))).toBe(3);
    expect(matchingPaths(revealed, "covers")).toEqual([]);
    expect(matchingPaths(revealed, "volume")).toEqual([]);
  });

  it("drops hidden paths from the changed list", () => {
    expect(revealedPaths(["music.volume", "tone", "series.tagline"], concealed)).toEqual(["tone"]);
  });

  it("finds nothing when only hidden fields match or changed", () => {
    const revealed = revealedFields(fields, concealed);
    const changed = revealedPaths(["music.volume"], concealed);
    const byQuery = settingsFilter(revealed, { query: "covers", changedOnly: false, changed });
    const byChange = settingsFilter(revealed, { query: "", changedOnly: true, changed });
    for (const rule of [byQuery, byChange]) {
      const visible = withoutConcealed(rule, concealed);
      expect(visible === undefined ? -1 : visiblePathSet(fields, visible).size).toBe(0);
    }
  });
});
