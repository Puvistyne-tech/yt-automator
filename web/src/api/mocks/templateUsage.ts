import { ruleConflict } from "@/api/mocks/db";
import type { MockState } from "@/api/mocks/fixtures/seed";
import type { Run, RunStatus } from "@/api/types";

export const DELETE_REMEDY = "move the automations to another pipeline and finish their runs first";
export const DRAFT_REMEDY =
  "it must stay ready until they move to another pipeline and their runs finish";

const OPEN_STATUSES: ReadonlySet<RunStatus> = new Set([
  "queued",
  "running",
  "publishing",
  "awaiting_review",
  "approved",
]);

export function isOpenRun(run: Pick<Run, "status" | "retry_at">): boolean {
  return OPEN_STATUSES.has(run.status) || (run.status === "failed" && run.retry_at !== null);
}

export function automationsUsing(state: MockState, typeId: string): string[] {
  return state.automations
    .filter((automation) => automation.pipeline_type === typeId)
    .map((automation) => automation.name)
    .sort();
}

export function runsUsing(state: MockState, typeId: string): string[] {
  return state.runs
    .filter((run) => run.pipeline_type === typeId && isOpenRun(run))
    .map((run) => run.id)
    .sort();
}

export function inUseMessage(automations: string[], runs: string[], remedy: string): string {
  const users = [
    ["automations", automations],
    ["open runs", runs],
  ] as const;
  const parts = users
    .filter(([, names]) => names.length > 0)
    .map(([kind, names]) => `${kind}: ${names.join(", ")}`);
  return `template is used by ${parts.join(" and ")}; ${remedy}`;
}

export function inUseConflict(state: MockState, typeId: string, remedy: string) {
  const automations = automationsUsing(state, typeId);
  const runs = runsUsing(state, typeId);
  if (automations.length === 0 && runs.length === 0) {
    return null;
  }
  return ruleConflict("template_in_use", inUseMessage(automations, runs, remedy));
}
