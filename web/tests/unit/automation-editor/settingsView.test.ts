import { describe, expect, it } from "vitest";
import {
  ADVANCED_PLATFORM_FIELDS,
  applicableAdvancedFields,
  basicVisibility,
  hiddenOptionsText,
  readSettingsView,
  revealsHiddenError,
  settingsErrorPaths,
  shownIn,
  simpleViewSummary,
  withErrorPaths,
} from "@/features/automation-editor/model/settingsView";
import { shownBy } from "@/shared/schema-form/fieldFilter";
import { schemaFields } from "@/shared/schema-form/schemaFields";

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

describe("shownIn", () => {
  it("shows the finer platform rules only in all settings", () => {
    expect(shownIn("all")("retry_policy")).toBe(true);
    expect(shownIn("simple")("retry_policy")).toBe(false);
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

const ERROR_PATTERNS = ADVANCED_PLATFORM_FIELDS.flatMap((field) =>
  field.errors.map((pattern) => pattern.replace("*", "0")),
);

describe("revealsHiddenError", () => {
  const visible = shownBy(["name"]);

  it.each(ERROR_PATTERNS)("spots an error on the finer rule %s", (path) => {
    expect(revealsHiddenError({ [path]: "x" }, visible)).toBe(true);
  });

  it.each(["schedule.every_hours", "review_policy.mode", "targets.0.channel_id"])(
    "ignores an error on the visible field %s",
    (path) => {
      expect(revealsHiddenError({ [path]: "x" }, visible)).toBe(false);
    },
  );

  it("spots errors on settings left out of the simple view", () => {
    expect(revealsHiddenError({ "settings.music.volume": "x" }, visible)).toBe(true);
    expect(revealsHiddenError({ "settings.name": "x" }, visible)).toBe(false);
  });

  it("ignores settings errors without ui:basic", () => {
    expect(revealsHiddenError({ settings: "x", "settings.music.volume": "x" }, undefined)).toBe(
      false,
    );
  });
});

describe("withErrorPaths", () => {
  const errors = { "settings.music.volume": "x", settings: "y", name: "z" };

  it("keeps fields with errors visible under any rule", () => {
    const visible = withErrorPaths(shownBy(["name"]), settingsErrorPaths(errors));
    expect(visible?.("music.volume")).toBe(true);
    expect(visible?.("music")).toBe(true);
    expect(visible?.("name")).toBe(true);
    expect(visible?.("music.enabled")).toBe(false);
  });

  it("leaves an unfiltered form unfiltered", () => {
    expect(withErrorPaths(undefined, ["music.volume"])).toBeUndefined();
  });

  it("names the settings paths that carry errors", () => {
    expect(settingsErrorPaths(errors)).toEqual(["music.volume"]);
  });
});

describe("applicableAdvancedFields", () => {
  const scheduled = { schedule: { kind: "interval" as const }, targets: [{}] };
  const manual = { schedule: { kind: "manual" as const }, targets: [] };

  it("lists every finer rule for a scheduled automation with targets", () => {
    expect(applicableAdvancedFields(scheduled)).toEqual(
      ADVANCED_PLATFORM_FIELDS.map((field) => field.id),
    );
  });

  it("skips schedule and target rules that are not shown", () => {
    expect(applicableAdvancedFields(manual)).toEqual([
      "description",
      "retry_policy",
      "reject_below",
    ]);
  });
});

describe("simpleViewSummary", () => {
  const fields = schemaFields(settingsSchema);

  it("counts hidden settings, applicable finer rules and hidden changes", () => {
    const summary = simpleViewSummary(fields, shownBy(["name"]), ["music.volume", "name"], 3);
    expect(summary).toEqual({ hidden: 5, changed: 1 });
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
