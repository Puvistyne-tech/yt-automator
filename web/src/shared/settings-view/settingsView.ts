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

export interface SimpleViewSummary {
  hidden: number;
  changed: number;
}

export function readSettingsView(stored: string | null): SettingsView {
  return SETTINGS_VIEWS.find((view) => view.id === stored)?.id ?? DEFAULT_VIEW;
}

export function basicVisibility(uiSchema: unknown): FieldVisibility | undefined {
  const paths = readBasicPaths(uiSchema);
  return paths === null ? undefined : shownBy(paths);
}

export function scopedErrorPaths(errors: Record<string, string>, scope: string): string[] {
  const prefix = `${scope}.`;
  return Object.keys(errors)
    .filter((path) => path.startsWith(prefix))
    .map((path) => path.slice(prefix.length));
}

export function hidesScopedError(
  errors: Record<string, string>,
  scope: string,
  visible: FieldVisibility | undefined,
): boolean {
  return visible !== undefined && scopedErrorPaths(errors, scope).some((path) => !visible(path));
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
