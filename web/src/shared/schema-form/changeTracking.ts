import type { Registry } from "@rjsf/utils";
import { useMemo, useRef } from "react";
import {
  type Concealed,
  type FieldPath,
  isChanged,
  resetRevealed,
  revealedChanges,
  type SettingPath,
  tracksChanges,
  valueAt,
} from "@/shared/schema-form/defaults";

type FormValue = Record<string, unknown>;
type Update = (value: FormValue) => FormValue;

export interface ChangeTracking {
  value: FormValue;
  defaults: FormValue;
  locked: boolean;
  concealed: Concealed | undefined;
  apply: (update: Update) => void;
}

export function useChangeTracking(
  value: FormValue,
  defaults: FormValue | undefined,
  onChange: (value: FormValue) => void,
  locked: boolean,
  concealed: Concealed | undefined,
): ChangeTracking | null {
  const latest = useRef({ value, onChange });
  latest.current = { value, onChange };
  return useMemo(() => {
    if (defaults === undefined) {
      return null;
    }
    const apply = (update: Update) => latest.current.onChange(update(latest.current.value));
    return { value, defaults, locked, concealed, apply };
  }, [value, defaults, locked, concealed]);
}

export function trackingOf(registry: Registry): ChangeTracking | null {
  const context = registry.formContext as { changes?: ChangeTracking | null } | undefined;
  return context?.changes ?? null;
}

function settingPath(path: FieldPath): SettingPath {
  return path.map(String);
}

function revealedIn(tracking: ChangeTracking, paths: readonly SettingPath[]): string[] {
  return revealedChanges(tracking.value, tracking.defaults, paths, tracking.concealed);
}

export function fieldChanged(tracking: ChangeTracking, path: FieldPath): boolean {
  if (tracking.concealed === undefined || !tracksChanges(path)) {
    return isChanged(tracking.value, tracking.defaults, path);
  }
  return revealedIn(tracking, [settingPath(path)]).length > 0;
}

export function fieldDefault(tracking: ChangeTracking, path: FieldPath): unknown {
  return valueAt(tracking.defaults, path);
}

export function changedIn(tracking: ChangeTracking, names: string[]): number {
  return revealedIn(
    tracking,
    names.map((name) => [name]),
  ).length;
}

function resetRevealedIn(tracking: ChangeTracking, paths: readonly SettingPath[]): void {
  tracking.apply((value) => resetRevealed(value, tracking.defaults, paths, tracking.concealed));
}

export function resetPath(tracking: ChangeTracking, path: FieldPath): void {
  resetRevealedIn(tracking, [settingPath(path)]);
}

export function resetSection(tracking: ChangeTracking, names: string[]): void {
  resetRevealedIn(
    tracking,
    names.map((name) => [name]),
  );
}
