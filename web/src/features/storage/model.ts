import type { CleanupAction, CleanupItem, CleanupReport, StorageReport } from "@/api/types";
import { formatBytes } from "@/shared/format/numbers";

export const ACTION_LABELS: Record<CleanupAction, string> = {
  delete_run: "Delete run and files",
  remove_intermediate: "Remove working files",
  remove_orphan: "Remove stray folder",
};

export function itemTitle(item: CleanupItem): string {
  if (item.action === "remove_orphan") {
    return `Folder ${item.run_id} (no run)`;
  }
  return `${item.automation_name} · ${item.run_id}`;
}

export function cleanupResultMessage(report: CleanupReport): string {
  const count = report.items.length;
  if (count === 0) {
    return "Nothing to clean up.";
  }
  const noun = count === 1 ? "item" : "items";
  return `Cleanup freed ${formatBytes(report.total_bytes)} from ${count} ${noun}.`;
}

function keepText(days: number, what: string): string {
  if (days === 0) {
    return `${what} are kept forever`;
  }
  return `${what} older than ${days} ${days === 1 ? "day" : "days"} go`;
}

export function policySummary(report: CleanupReport): string {
  const runs = keepText(report.keep_runs_days, "finished runs");
  const files = keepText(report.keep_intermediate_days, "working files");
  return `Uses the saved settings: ${runs}; ${files}. Runs waiting for review, approved or still uploading are never touched.`;
}

export function share(part: number, whole: number): number {
  return whole <= 0 ? 0 : Math.round((part / whole) * 100);
}

export interface UsageSummary {
  runs_bytes: number;
  working_bytes: number;
  final_share: number;
  free_label: string;
  stray_hint: string | undefined;
}

export function usageSummary(report: StorageReport): UsageSummary {
  const runs = report.final_bytes + report.intermediate_bytes + report.orphan_bytes;
  return {
    runs_bytes: runs,
    working_bytes: report.intermediate_bytes + report.orphan_bytes,
    final_share: share(report.final_bytes, runs),
    free_label: report.free_bytes === null ? "Unknown" : formatBytes(report.free_bytes),
    stray_hint:
      report.orphan_bytes > 0 ? `${formatBytes(report.orphan_bytes)} in stray folders` : undefined,
  };
}
