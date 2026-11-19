import { isJsonObject } from "@/shared/isJsonObject";

export type FieldPath = readonly (string | number)[];

const PREVIEW_LENGTH = 48;

function child(source: unknown, key: string | number): unknown {
  if (Array.isArray(source) && typeof key === "number") {
    return source[key];
  }
  return isJsonObject(source) ? source[String(key)] : undefined;
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
  return { ...(isJsonObject(source) ? source : {}), [head]: inner } as T;
}

function sameObjects(a: Record<string, unknown>, b: Record<string, unknown>): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  return [...keys].every((key) => sameSettingValue(a[key], b[key]));
}

export function sameSettingValue(a: unknown, b: unknown): boolean {
  if (a === undefined || a === null || b === undefined || b === null) {
    return (a ?? null) === (b ?? null);
  }
  if (Array.isArray(a) || Array.isArray(b)) {
    return (
      Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((item, index) => sameSettingValue(item, b[index]))
    );
  }
  if (isJsonObject(a) && isJsonObject(b)) {
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
    tracksChanges(path) &&
    fallback !== undefined &&
    !sameSettingValue(valueAt(value, path), fallback)
  );
}

function changedLeaves(value: unknown, defaults: unknown, path: string[]): string[] {
  const fallback = valueAt(defaults, path);
  const current = valueAt(value, path);
  if (isJsonObject(fallback) && isJsonObject(current)) {
    return Object.keys(fallback).flatMap((key) => changedLeaves(value, defaults, [...path, key]));
  }
  return isChanged(value, defaults, path) ? [path.join(".")] : [];
}

export function changedPaths(value: unknown, defaults: unknown, names: string[]): string[] {
  return names.flatMap((name) => changedLeaves(value, defaults, [name]));
}

export function changedCount(value: unknown, defaults: unknown, names: string[]): number {
  return changedPaths(value, defaults, names).length;
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
  if (isJsonObject(value)) {
    return "default values";
  }
  return String(value) === "" ? "empty" : shortened(String(value));
}
