import type { ScheduleKind } from "@/api/types";

export function enabledSwitchLabel(kind: ScheduleKind): string {
  return kind === "manual"
    ? "Enabled (manual schedule: runs only start from Run now)"
    : "Enabled: run on schedule";
}
