import { RUN_STATUS_ORDER } from "@/api/labels";
import type { RunFilters, RunStatus } from "@/api/types";

export const RUN_LIST_LIMIT = 100;

function isRunStatus(value: string | null): value is RunStatus {
  return value !== null && (RUN_STATUS_ORDER as string[]).includes(value);
}

export function readFilters(params: URLSearchParams): RunFilters {
  const automation = params.get("automation_id");
  const status = params.get("status");
  return {
    ...(automation ? { automation_id: automation } : {}),
    ...(isRunStatus(status) ? { status } : {}),
    limit: RUN_LIST_LIMIT,
  };
}

export function withFilter(
  params: URLSearchParams,
  key: "automation_id" | "status",
  value: string,
): URLSearchParams {
  const next = new URLSearchParams(params);
  if (value === "") {
    next.delete(key);
  } else {
    next.set(key, value);
  }
  return next;
}

export function hasActiveFilters(filters: RunFilters): boolean {
  return filters.automation_id !== undefined || filters.status !== undefined;
}
