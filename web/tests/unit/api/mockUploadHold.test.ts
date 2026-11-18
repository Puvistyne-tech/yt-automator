import { makeArtifact, makeRun, makeTarget, makeUpload } from "@/api/mocks/fixtures/factories";
import { cleanupAction } from "@/api/mocks/retention";
import { holdsRun, latestRelease } from "@/api/mocks/uploadHold";
import type { Run, Target } from "@/api/types";

const DAY_MS = 86_400_000;
const NOW = Date.parse("2026-03-01T00:00:00Z");
const POLICY = { keep_runs_days: 30, keep_intermediate_days: 7, publish_targets: {} };
const LEGACY = makeUpload({ privacy: "public", target_id: "target-late", publish_at: null });

function oldRun(overrides: Partial<Run> = {}): Run {
  return makeRun({
    id: "run-old",
    status: "published",
    finished_at: new Date(NOW - 40 * DAY_MS).toISOString(),
    artifacts: [makeArtifact()],
    ...overrides,
  });
}

function targets(overrides: Partial<Target>): Record<string, Target> {
  return { "target-late": makeTarget({ id: "target-late", ...overrides }) };
}

describe("mock upload hold", () => {
  it("holds an older public upload for its target delay and when the target is gone", () => {
    const run = oldRun({ uploads: [LEGACY] });
    expect(cleanupAction(run, NOW, POLICY)).toBeNull();
    const delayed = { ...POLICY, publish_targets: targets({ publish_delay_minutes: 50 * 1440 }) };
    expect(cleanupAction(run, NOW, delayed)).toBeNull();
    expect(cleanupAction(run, NOW + 10 * DAY_MS, delayed)).toBe("delete_run");
    expect(cleanupAction(oldRun({ uploads: [makeUpload()] }), NOW, POLICY)).toBe("delete_run");
  });

  it("holds an older upload until its target time of day after the run finished", () => {
    const finished = Date.parse("2026-01-05T23:00:00Z");
    const release = Date.parse("2026-01-06T06:30:00Z");
    const daily = targets({ publish_time_of_day: "06:30", publish_timezone: "UTC" });
    expect(latestRelease(daily["target-late"] as Target, finished)).toBe(release);
    expect(holdsRun(LEGACY, finished, release - 1000, daily)).toBe(true);
    expect(holdsRun(LEGACY, finished, release, daily)).toBe(false);
    const unknown = targets({ publish_time_of_day: "06:30", publish_timezone: "Mars/Base" });
    expect(holdsRun(LEGACY, finished, release + 400 * DAY_MS, unknown)).toBe(true);
  });

  it("never touches a failed run waiting for an automatic retry", () => {
    const later = new Date(NOW + DAY_MS).toISOString();
    expect(cleanupAction(oldRun({ status: "failed", retry_at: later }), NOW, POLICY)).toBeNull();
    expect(cleanupAction(oldRun({ status: "failed", retry_at: null }), NOW, POLICY)).toBe(
      "delete_run",
    );
  });
});
