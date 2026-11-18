export type FieldPath = readonly (string | number)[];
type PlainObject = Record<string, unknown>;

const PREVIEW_LENGTH = 48;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function child(source: unknown, key: string | number): unknown {
  if (Array.isArray(source) && typeof key === "number") {
    return source[key];
  }
  return isPlainObject(source) ? source[String(key)] : undefined;
}

export function valueAt(source: unknown, path: FieldPath): unknown {
  return path.reduce<unknown>((node, key) => child(node, key), source);
}

export function withValueAt<T>(source: T, path: FieldPath, value: unknown): T {
  const [head, ...rest] = path;
  if (head === undefined) {
    return value as T;
  }
  const inner = withValueAt(child(source, head), rest, value);
  if (Array.isArray(source) && typeof head === "number") {
    return source.map((item, index) => (index === head ? inner : item)) as T;
  }
  return { ...(isPlainObject(source) ? source : {}), [head]: inner } as T;
}

function sameObjects(a: PlainObject, b: PlainObject): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  return [...keys].every((key) => sameValue(a[key], b[key]));
}

export function sameValue(a: unknown, b: unknown): boolean {
  if (a === undefined || a === null || b === undefined || b === null) {
    return (a ?? null) === (b ?? null);
  }
  if (Array.isArray(a) || Array.isArray(b)) {
    return (
      Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((item, index) => sameValue(item, b[index]))
    );
  }
  if (isPlainObject(a) && isPlainObject(b)) {
    return sameObjects(a, b);
  }
  return a === b;
}

export function tracksChanges(path: FieldPath): boolean {
  return path.length > 0 && path.every((segment) => typeof segment === "string");
}

export function isChanged(value: unknown, defaults: unknown, path: FieldPath): boolean {
  const fallback = valueAt(defaults, path);
  return (
    tracksChanges(path) && fallback !== undefined && !sameValue(valueAt(value, path), fallback)
  );
}

function changedLeaves(value: unknown, defaults: unknown, path: FieldPath): number {
  const fallback = valueAt(defaults, path);
  const current = valueAt(value, path);
  if (isPlainObject(fallback) && isPlainObject(current)) {
    return Object.keys(fallback).reduce(
      (total, key) => total + changedLeaves(value, defaults, [...path, key]),
      0,
    );
  }
  return isChanged(value, defaults, path) ? 1 : 0;
}

export function changedCount(value: unknown, defaults: unknown, names: string[]): number {
  return names.reduce((total, name) => total + changedLeaves(value, defaults, [name]), 0);
}

export function resetField<T>(value: T, defaults: unknown, path: FieldPath): T {
  const fallback = valueAt(defaults, path);
  return fallback === undefined ? value : withValueAt(value, path, structuredClone(fallback));
}

export function resetFields<T>(value: T, defaults: unknown, names: string[]): T {
  return names.reduce((next, name) => resetField(next, defaults, [name]), value);
}

function shortened(text: string): string {
  return text.length > PREVIEW_LENGTH ? `${text.slice(0, PREVIEW_LENGTH - 1)}…` : text;
}

function listPreview(items: unknown[]): string {
  if (items.length === 0) {
    return "no items";
  }
  return items.length === 1 ? "1 item" : `${items.length} items`;
}

export function defaultPreview(value: unknown): string {
  if (value === null || value === undefined) {
    return "not set";
  }
  if (typeof value === "boolean") {
    return value ? "on" : "off";
  }
  if (Array.isArray(value)) {
    return listPreview(value);
  }
  if (isPlainObject(value)) {
    return "default values";
  }
  return String(value) === "" ? "empty" : shortened(String(value));
}
