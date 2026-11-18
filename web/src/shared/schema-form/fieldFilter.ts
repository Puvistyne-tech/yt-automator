import { isJsonObject } from "@/shared/isJsonObject";
import type { SchemaField } from "@/shared/schema-form/schemaFields";

export type FieldVisibility = (path: string) => boolean;

export interface FilterChoice {
  query: string;
  changedOnly: boolean;
  changed: readonly string[];
}

export const BASIC_KEY = "ui:basic";

export function readBasicPaths(uiSchema: unknown): string[] | null {
  const raw = isJsonObject(uiSchema) ? uiSchema[BASIC_KEY] : undefined;
  if (!Array.isArray(raw)) {
    return null;
  }
  return raw.filter((entry): entry is string => typeof entry === "string");
}

function within(path: string, ancestor: string): boolean {
  return path === ancestor || path.startsWith(`${ancestor}.`);
}

export function shownBy(paths: readonly string[]): FieldVisibility {
  return (path) => paths.some((listed) => within(path, listed) || within(listed, path));
}

export function matchingPaths(fields: readonly SchemaField[], query: string): string[] {
  const needle = query.trim().toLowerCase();
  return fields
    .filter((field) => `${field.title}\n${field.description}`.toLowerCase().includes(needle))
    .map((field) => field.path);
}

export function settingsFilter(
  fields: readonly SchemaField[],
  { query, changedOnly, changed }: FilterChoice,
): FieldVisibility | undefined {
  const searching = query.trim() !== "";
  if (!searching && !changedOnly) {
    return undefined;
  }
  const byQuery = searching ? shownBy(matchingPaths(fields, query)) : () => true;
  const byChange = changedOnly ? shownBy(changed) : () => true;
  return (path) => byQuery(path) && byChange(path);
}

export function visiblePathSet(
  fields: readonly SchemaField[],
  visible: FieldVisibility,
): ReadonlySet<string> {
  return new Set(fields.filter((field) => visible(field.path)).map((field) => field.path));
}

export function visibleProperties<T extends { name: string }>(
  properties: T[],
  parent: readonly (string | number)[],
  visible: ReadonlySet<string> | undefined,
): T[] {
  if (visible === undefined || parent.some((segment) => typeof segment === "number")) {
    return properties;
  }
  return properties.filter((property) => visible.has([...parent, property.name].join(".")));
}

export function visibleLeafCount(fields: readonly SchemaField[], visible: FieldVisibility): number {
  return fields.filter((field) => field.leaf && visible(field.path)).length;
}

export function hiddenLeafCount(fields: readonly SchemaField[], visible: FieldVisibility): number {
  return fields.filter((field) => field.leaf && !visible(field.path)).length;
}
