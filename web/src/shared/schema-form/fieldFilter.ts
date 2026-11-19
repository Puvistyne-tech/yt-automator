import { isJsonObject } from "@/shared/isJsonObject";
import type { SchemaField } from "@/shared/schema-form/schemaFields";

export type FieldVisibility = (path: string) => boolean;

export interface FilterChoice {
  query: string;
  changedOnly: boolean;
  changed: readonly string[];
}

export const BASIC_KEY = "ui:basic";
export const HIDDEN_KEY = "ui:hidden";

function listedPaths(uiSchema: unknown, key: string): string[] | null {
  const raw = isJsonObject(uiSchema) ? uiSchema[key] : undefined;
  if (!Array.isArray(raw)) {
    return null;
  }
  return raw.filter((entry): entry is string => typeof entry === "string");
}

export function readBasicPaths(uiSchema: unknown): string[] | null {
  return listedPaths(uiSchema, BASIC_KEY);
}

export function readHiddenPaths(uiSchema: unknown): string[] {
  return listedPaths(uiSchema, HIDDEN_KEY) ?? [];
}

function within(path: string, ancestor: string): boolean {
  return path === ancestor || path.startsWith(`${ancestor}.`);
}

function leavesUnder(fields: readonly SchemaField[], parent: string): SchemaField[] {
  return fields.filter((field) => field.leaf && field.path.startsWith(`${parent}.`));
}

export function concealedBy(
  fields: readonly SchemaField[],
  paths: readonly string[],
): FieldVisibility | undefined {
  if (paths.length === 0) {
    return undefined;
  }
  const listed = (path: string) => paths.some((hidden) => within(path, hidden));
  const emptied = new Set(
    fields
      .filter(
        (field) =>
          !field.leaf && leavesUnder(fields, field.path).every((leaf) => listed(leaf.path)),
      )
      .map((field) => field.path),
  );
  return (path) => listed(path) || emptied.has(path);
}

export function withoutConcealed(
  rule: FieldVisibility | undefined,
  concealed: FieldVisibility | undefined,
): FieldVisibility | undefined {
  if (concealed === undefined) {
    return rule;
  }
  return (path) => !concealed(path) && (rule === undefined || rule(path));
}

export function revealedPaths(
  paths: readonly string[],
  concealed: FieldVisibility | undefined,
): readonly string[] {
  return concealed === undefined ? paths : paths.filter((path) => !concealed(path));
}

export function revealedFields(
  fields: readonly SchemaField[],
  concealed: FieldVisibility | undefined,
): readonly SchemaField[] {
  return concealed === undefined ? fields : fields.filter((field) => !concealed(field.path));
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

function showsWholly(parent: string, visible: ReadonlySet<string>): boolean {
  const head = `${parent}.`;
  return visible.has(parent) && ![...visible].some((path) => path.startsWith(head));
}

export function visibleProperties<T extends { name: string }>(
  properties: T[],
  parent: readonly (string | number)[],
  visible: ReadonlySet<string> | undefined,
): T[] {
  if (visible === undefined || parent.some((segment) => typeof segment === "number")) {
    return properties;
  }
  const prefix = parent.join(".");
  if (prefix !== "" && showsWholly(prefix, visible)) {
    return properties;
  }
  return properties.filter((property) => visible.has([...parent, property.name].join(".")));
}

export function hiddenLeafCount(fields: readonly SchemaField[], visible: FieldVisibility): number {
  return fields.filter((field) => field.leaf && !visible(field.path)).length;
}
