import { describe, expect, it } from "vitest";
import {
  ADVANCED_PLATFORM_FIELDS,
  basicVisibility,
  hiddenOptionsText,
  readSettingsView,
  revealsHiddenError,
  shownIn,
  simpleViewSummary,
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

describe("revealsHiddenError", () => {
  const visible = shownBy(["name"]);

  it("spots errors on finer platform rules, including inside targets", () => {
    expect(revealsHiddenError({ "retry_policy.delay_minutes": "x" }, visible)).toBe(true);
    expect(revealsHiddenError({ "targets.2.publish_timezone": "x" }, visible)).toBe(true);
    expect(revealsHiddenError({ "schedule.max_runs_per_day": "x" }, visible)).toBe(true);
  });

  it("spots errors on settings left out of the simple view", () => {
    expect(revealsHiddenError({ "settings.music.volume": "x" }, visible)).toBe(true);
    expect(revealsHiddenError({ "settings.name": "x" }, visible)).toBe(false);
  });

  it("ignores errors that stay visible", () => {
    expect(revealsHiddenError({ name: "x", "targets.0.channel_id": "x" }, visible)).toBe(false);
    expect(revealsHiddenError({ settings: "x", "settings.music.volume": "x" }, undefined)).toBe(
      false,
    );
    expect(revealsHiddenError({ "schedule.every_hours": "x" }, visible)).toBe(false);
  });
});

describe("simpleViewSummary", () => {
  const fields = schemaFields(settingsSchema);

  it("counts hidden settings, finer rules and hidden changes", () => {
    const summary = simpleViewSummary(fields, shownBy(["name"]), ["music.volume", "name"]);
    expect(summary).toEqual({ hidden: 2 + ADVANCED_PLATFORM_FIELDS.length, changed: 1 });
  });

  it("counts only the finer rules without ui:basic", () => {
    const summary = simpleViewSummary(fields, undefined, ["music.volume"]);
    expect(summary).toEqual({ hidden: ADVANCED_PLATFORM_FIELDS.length, changed: 0 });
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
