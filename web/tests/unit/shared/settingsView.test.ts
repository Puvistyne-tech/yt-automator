import { describe, expect, it } from "vitest";
import {
  concealedBy,
  revealedFields,
  revealedPaths,
  settingsFilter,
  shownBy,
  withoutConcealed,
} from "@/shared/schema-form/fieldFilter";
import { schemaFields } from "@/shared/schema-form/schemaFields";
import {
  basicVisibility,
  hiddenOptionsText,
  hidesScopedError,
  readSettingsView,
  scopedErrorPaths,
  simpleViewSummary,
  withErrorPaths,
} from "@/shared/settings-view/settingsView";

const settingsSchema = {
  type: "object",
  properties: {
    name: { type: "string", title: "Name" },
    music: {
      type: "object",
      title: "Music",
      properties: { enabled: { type: "boolean" }, volume: { type: "number" } },
    },
  },
};

describe("readSettingsView", () => {
  it("accepts the two stored views and falls back to simple", () => {
    expect(readSettingsView("all")).toBe("all");
    expect(readSettingsView("simple")).toBe("simple");
    expect(readSettingsView(null)).toBe("simple");
    expect(readSettingsView("other")).toBe("simple");
  });
});

describe("basicVisibility", () => {
  it("reads ui:basic from the pipeline ui schema", () => {
    const visible = basicVisibility({ "ui:basic": ["music.enabled"] });
    expect(visible?.("music.enabled")).toBe(true);
    expect(visible?.("music.volume")).toBe(false);
  });

  it("leaves the form unfiltered without ui:basic", () => {
    expect(basicVisibility({})).toBeUndefined();
    expect(basicVisibility(undefined)).toBeUndefined();
  });
});

describe("withErrorPaths", () => {
  const errors = { "settings.music.volume": "x", settings: "y", name: "z" };

  it("keeps fields with errors visible under any rule", () => {
    const visible = withErrorPaths(shownBy(["name"]), scopedErrorPaths(errors, "settings"));
    expect(visible?.("music.volume")).toBe(true);
    expect(visible?.("music")).toBe(true);
    expect(visible?.("name")).toBe(true);
    expect(visible?.("music.enabled")).toBe(false);
  });

  it("shows a hidden field that has an error, with its parent, despite the search", () => {
    const fields = schemaFields(settingsSchema);
    const concealed = concealedBy(fields, ["music"]);
    const searched = settingsFilter(revealedFields(fields, concealed), {
      query: "zebra",
      changedOnly: false,
      changed: [],
    });
    const visible = withErrorPaths(withoutConcealed(searched, concealed), ["music.volume"]);
    expect(visible?.("music.volume")).toBe(true);
    expect(visible?.("music")).toBe(true);
    expect(visible?.("music.enabled")).toBe(false);
    expect(visible?.("name")).toBe(false);
  });

  it("leaves an unfiltered form unfiltered", () => {
    expect(withErrorPaths(undefined, ["music.volume"])).toBeUndefined();
  });

  it("names the paths that carry errors within a scope", () => {
    expect(scopedErrorPaths(errors, "settings")).toEqual(["music.volume"]);
    expect(scopedErrorPaths(errors, "definition")).toEqual([]);
  });
});

describe("simpleViewSummary", () => {
  const fields = schemaFields(settingsSchema);

  it("counts hidden settings, applicable finer rules and hidden changes", () => {
    const summary = simpleViewSummary(fields, shownBy(["name"]), ["music.volume", "name"], 3);
    expect(summary).toEqual({ hidden: 5, changed: 1 });
  });

  it("leaves hidden settings and their changes out of the counts", () => {
    const concealed = concealedBy(fields, ["music.volume"]);
    const changed = revealedPaths(["music.volume", "music.enabled"], concealed);
    const summary = simpleViewSummary(
      revealedFields(fields, concealed),
      shownBy(["name"]),
      changed,
      3,
    );
    expect(summary).toEqual({ hidden: 4, changed: 1 });
  });

  it("counts only the finer rules without ui:basic", () => {
    const summary = simpleViewSummary(fields, undefined, ["music.volume"], 3);
    expect(summary).toEqual({ hidden: 3, changed: 0 });
  });
});

describe("hiddenOptionsText", () => {
  it("names the hidden options and changes in plain words", () => {
    expect(hiddenOptionsText({ hidden: 12, changed: 3 })).toBe(
      "12 more options in All settings, 3 changed.",
    );
    expect(hiddenOptionsText({ hidden: 1, changed: 0 })).toBe("1 more option in All settings.");
  });
});

describe("hidesScopedError", () => {
  it("spots an error within the scope on a field the rule hides", () => {
    const errors = { "definition.music.volume": "x" };
    expect(hidesScopedError(errors, "definition", shownBy(["name"]))).toBe(true);
    expect(hidesScopedError(errors, "definition", shownBy(["music"]))).toBe(false);
    expect(hidesScopedError(errors, "settings", shownBy(["name"]))).toBe(false);
    expect(hidesScopedError(errors, "definition", undefined)).toBe(false);
  });
});
