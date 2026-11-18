export type RunNowState =
  | { kind: "hidden" }
  | { kind: "ready" }
  | { kind: "blocked"; reason: string };

export const UNSAVED_RUN_REASON = "Save your changes first: a run uses the saved settings.";

export function runNowState(automationId: string | undefined, dirty: boolean): RunNowState {
  if (automationId === undefined) {
    return { kind: "hidden" };
  }
  return dirty ? { kind: "blocked", reason: UNSAVED_RUN_REASON } : { kind: "ready" };
}
