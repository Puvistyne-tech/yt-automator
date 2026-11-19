import { describe, expect, it } from "vitest";
import {
  ADVANCED_PLATFORM_FIELDS,
  applicableAdvancedFields,
  revealsHiddenError,
  settingsErrorPaths,
  shownIn,
} from "@/features/automation-editor/model/settingsView";
import { shownBy } from "@/shared/schema-form/fieldFilter";

describe("shownIn", () => {
  it("shows the finer platform rules only in all settings", () => {
    expect(shownIn("all")("retry_policy")).toBe(true);
    expect(shownIn("simple")("retry_policy")).toBe(false);
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

describe("settingsErrorPaths", () => {
  it("names the settings paths that carry errors", () => {
    expect(settingsErrorPaths({ "settings.music.volume": "x", settings: "y" })).toEqual([
      "music.volume",
    ]);
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
