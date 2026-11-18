import type { Run } from "@/api/types";

export function runPath(run: Pick<Run, "id">): string {
  return `/runs/${encodeURIComponent(run.id)}`;
}
