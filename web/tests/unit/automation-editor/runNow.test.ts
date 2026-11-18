import { enabledSwitchLabel } from "@/features/automation-editor/model/general";
import { runNowState } from "@/features/automation-editor/model/runNow";

describe("runNowState", () => {
  it("hides Run now for an automation that was never saved", () => {
    expect(runNowState(undefined, false)).toEqual({ kind: "hidden" });
    expect(runNowState(undefined, true)).toEqual({ kind: "hidden" });
  });

  it("offers Run now for a saved automation without changes", () => {
    expect(runNowState("auto-1", false)).toEqual({ kind: "ready" });
  });

  it("blocks Run now with a reason while there are unsaved changes", () => {
    expect(runNowState("auto-1", true)).toEqual({
      kind: "blocked",
      reason: "Save your changes first: a run uses the saved settings.",
    });
  });
});

describe("enabledSwitchLabel", () => {
  it("explains that a manual automation only runs when started by hand", () => {
    expect(enabledSwitchLabel("manual")).toBe(
      "Enabled (manual schedule: runs only start from Run now)",
    );
  });

  it.each(["interval", "cron"] as const)("says a %s automation runs on its schedule", (kind) => {
    expect(enabledSwitchLabel(kind)).toBe("Enabled: run on schedule");
  });
});
