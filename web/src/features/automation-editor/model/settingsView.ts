import type { FieldErrors } from "@/api/errors";
import type { ScheduleKind } from "@/api/types";
import type { FieldVisibility } from "@/shared/schema-form/fieldFilter";
import {
  hidesScopedError,
  type SettingsView,
  scopedErrorPaths,
} from "@/shared/settings-view/settingsView";

const SETTINGS_SCOPE = "settings";
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

export function settingsErrorPaths(errors: FieldErrors): string[] {
  return scopedErrorPaths(errors, SETTINGS_SCOPE);
}

function matchesPattern(path: string, pattern: string): boolean {
  const segments = path.split(".");
  return pattern
    .split(".")
    .every((part, index) => part === ANY_SEGMENT || part === segments[index]);
}

function isAdvancedPlatformPath(path: string): boolean {
  return ADVANCED_PLATFORM_FIELDS.some((field) =>
    field.errors.some((pattern) => matchesPattern(path, pattern)),
  );
}

export function revealsHiddenError(
  errors: FieldErrors,
  settingsVisible: FieldVisibility | undefined,
): boolean {
  return (
    hidesScopedError(errors, SETTINGS_SCOPE, settingsVisible) ||
    Object.keys(errors).some(isAdvancedPlatformPath)
  );
}
