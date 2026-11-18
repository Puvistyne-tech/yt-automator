import type { FieldErrors } from "@/api/errors";
import { pluralize } from "@/shared/format/text";
import {
  type FieldVisibility,
  hiddenLeafCount,
  readBasicPaths,
  shownBy,
} from "@/shared/schema-form/fieldFilter";
import type { SchemaField } from "@/shared/schema-form/schemaFields";

export type SettingsView = "simple" | "all";

export const SETTINGS_VIEWS: readonly { id: SettingsView; label: string }[] = [
  { id: "simple", label: "Simple" },
  { id: "all", label: "All settings" },
];

export const SETTINGS_VIEW_STORAGE_KEY = "autotube.editor.settings-view";
const DEFAULT_VIEW: SettingsView = "simple";
const SETTINGS_PREFIX = "settings.";
const ANY_SEGMENT = "*";

export const ADVANCED_PLATFORM_FIELDS = [
  { id: "description", errors: ["description"] },
  { id: "timezone", errors: ["schedule.timezone"] },
  {
    id: "schedule_limits",
    errors: [
      "schedule.active_from",
      "schedule.active_until",
      "schedule.max_runs_per_day",
      "schedule.skip_if_unfinished",
    ],
  },
  { id: "retry_policy", errors: ["retry_policy"] },
  { id: "playlist", errors: ["targets.*.playlist_id"] },
  {
    id: "publish_timing",
    errors: [
      "targets.*.publish_delay_minutes",
      "targets.*.publish_time_of_day",
      "targets.*.publish_timezone",
    ],
  },
  { id: "reject_below", errors: ["review_policy.reject_below"] },
] as const;

export type AdvancedField = (typeof ADVANCED_PLATFORM_FIELDS)[number]["id"];
export type PlatformShows = (field: AdvancedField) => boolean;

export interface SimpleViewSummary {
  hidden: number;
  changed: number;
}

export function readSettingsView(stored: string | null): SettingsView {
  return SETTINGS_VIEWS.find((view) => view.id === stored)?.id ?? DEFAULT_VIEW;
}

export function shownIn(view: SettingsView): PlatformShows {
  return () => view === "all";
}

export function basicVisibility(uiSchema: unknown): FieldVisibility | undefined {
  const paths = readBasicPaths(uiSchema);
  return paths === null ? undefined : shownBy(paths);
}

function matchesPattern(path: string, pattern: string): boolean {
  const segments = path.split(".");
  return pattern
    .split(".")
    .every((part, index) => part === ANY_SEGMENT || part === segments[index]);
}

function hiddenInSimple(path: string, settingsVisible: FieldVisibility | undefined): boolean {
  if (path.startsWith(SETTINGS_PREFIX)) {
    return settingsVisible !== undefined && !settingsVisible(path.slice(SETTINGS_PREFIX.length));
  }
  return ADVANCED_PLATFORM_FIELDS.some((field) =>
    field.errors.some((pattern) => matchesPattern(path, pattern)),
  );
}

export function revealsHiddenError(
  errors: FieldErrors,
  settingsVisible: FieldVisibility | undefined,
): boolean {
  return Object.keys(errors).some((path) => hiddenInSimple(path, settingsVisible));
}

export function simpleViewSummary(
  fields: readonly SchemaField[],
  settingsVisible: FieldVisibility | undefined,
  changed: readonly string[],
): SimpleViewSummary {
  const platform = ADVANCED_PLATFORM_FIELDS.length;
  if (settingsVisible === undefined) {
    return { hidden: platform, changed: 0 };
  }
  return {
    hidden: hiddenLeafCount(fields, settingsVisible) + platform,
    changed: changed.filter((path) => !settingsVisible(path)).length,
  };
}

export function hiddenOptionsText({ hidden, changed }: SimpleViewSummary): string {
  const options = `${pluralize(hidden, "more option")} in All settings`;
  return changed > 0 ? `${options}, ${changed} changed.` : `${options}.`;
}
