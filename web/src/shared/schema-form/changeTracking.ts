import type { Registry } from "@rjsf/utils";
import { useMemo, useRef } from "react";
import {
  changedCount,
  type FieldPath,
  isChanged,
  resetField,
  resetFields,
  valueAt,
} from "@/shared/schema-form/defaults";

type FormValue = Record<string, unknown>;
type Update = (value: FormValue) => FormValue;

export interface ChangeTracking {
  value: FormValue;
  defaults: FormValue;
  locked: boolean;
  apply: (update: Update) => void;
}

export function useChangeTracking(
  value: FormValue,
  defaults: FormValue | undefined,
  onChange: (value: FormValue) => void,
  locked: boolean,
): ChangeTracking | null {
  const latest = useRef({ value, onChange });
  latest.current = { value, onChange };
  return useMemo(() => {
    if (defaults === undefined) {
      return null;
    }
    const apply = (update: Update) => latest.current.onChange(update(latest.current.value));
    return { value, defaults, locked, apply };
  }, [value, defaults, locked]);
}

export function trackingOf(registry: Registry): ChangeTracking | null {
  const context = registry.formContext as { changes?: ChangeTracking | null } | undefined;
  return context?.changes ?? null;
}

export function fieldChanged(tracking: ChangeTracking, path: FieldPath): boolean {
  return isChanged(tracking.value, tracking.defaults, path);
}

export function fieldDefault(tracking: ChangeTracking, path: FieldPath): unknown {
  return valueAt(tracking.defaults, path);
}

export function changedIn(tracking: ChangeTracking, names: string[]): number {
  return changedCount(tracking.value, tracking.defaults, names);
}

export function resetPath(tracking: ChangeTracking, path: FieldPath): void {
  tracking.apply((value) => resetField(value, tracking.defaults, path));
}

export function resetSection(tracking: ChangeTracking, names: string[]): void {
  tracking.apply((value) => resetFields(value, tracking.defaults, names));
}
