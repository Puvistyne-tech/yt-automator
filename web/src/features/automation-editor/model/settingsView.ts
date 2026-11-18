import type { FieldErrors } from "@/api/errors";
import type { ScheduleKind } from "@/api/types";
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
  { id: "description", needs: "always", errors: ["description"] },
  { id: "timezone", needs: "schedule", errors: ["schedule.timezone"] },
  {
    id: "schedule_limits",
    needs: "schedule",
    errors: [
      "schedule.active_from",
      "schedule.active_until",
      "schedule.max_runs_per_day",
      "schedule.skip_if_unfinished",
    ],
  },
  { id: "retry_policy", needs: "always", errors: ["retry_policy"] },
  { id: "playlist", needs: "targets", errors: ["targets.*.playlist_id"] },
  {
    id: "publish_timing",
    needs: "targets",
    errors: [
      "targets.*.publish_delay_minutes",
      "targets.*.publish_time_of_day",
      "targets.*.publish_timezone",
    ],
  },
  { id: "reject_below", needs: "always", errors: ["review_policy.reject_below"] },
] as const;

export type AdvancedField = (typeof ADVANCED_PLATFORM_FIELDS)[number]["id"];
export type PlatformShows = (field: AdvancedField) => boolean;
type Need = (typeof ADVANCED_PLATFORM_FIELDS)[number]["needs"];

export interface PlatformDraft {
  schedule: { kind: ScheduleKind };
  targets: readonly unknown[];
}

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

function needMet(need: Need, draft: PlatformDraft): boolean {
  if (need === "schedule") {
    return draft.schedule.kind !== "manual";
  }
  return need === "targets" ? draft.targets.length > 0 : true;
}

export function applicableAdvancedFields(draft: PlatformDraft): AdvancedField[] {
  return ADVANCED_PLATFORM_FIELDS.filter((field) => needMet(field.needs, draft)).map(
    (field) => field.id,
  );
}

export function basicVisibility(uiSchema: unknown): FieldVisibility | undefined {
  const paths = readBasicPaths(uiSchema);
  return paths === null ? undefined : shownBy(paths);
}

export function settingsErrorPaths(errors: FieldErrors): string[] {
  return Object.keys(errors)
    .filter((path) => path.startsWith(SETTINGS_PREFIX))
    .map((path) => path.slice(SETTINGS_PREFIX.length));
}

export function withErrorPaths(
  rule: FieldVisibility | undefined,
  errorPaths: readonly string[],
): FieldVisibility | undefined {
  if (rule === undefined) {
    return undefined;
  }
  const erroneous = shownBy(errorPaths);
  return (path) => rule(path) || erroneous(path);
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
  hiddenRules: number,
): SimpleViewSummary {
  if (settingsVisible === undefined) {
    return { hidden: hiddenRules, changed: 0 };
  }
  return {
    hidden: hiddenLeafCount(fields, settingsVisible) + hiddenRules,
    changed: changed.filter((path) => !settingsVisible(path)).length,
  };
}

export function hiddenOptionsText({ hidden, changed }: SimpleViewSummary): string {
  const options = `${pluralize(hidden, "more option")} in All settings`;
  return changed > 0 ? `${options}, ${changed} changed.` : `${options}.`;
}
