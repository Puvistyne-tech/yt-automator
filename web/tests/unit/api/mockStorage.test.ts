import { api } from "@/api/client";
import { db } from "@/api/mocks/db";
import { makeArtifact, makeRun, makeUpload } from "@/api/mocks/fixtures/factories";
import { cleanupAction, cleanupItems, hasIntermediateWork } from "@/api/mocks/retention";
import type { AppSettings, CleanupReport, Run, StorageReport } from "@/api/types";

const DAY_MS = 86_400_000;
const NOW = Date.parse("2026-03-01T00:00:00Z");
const POLICY = { keep_runs_days: 30, keep_intermediate_days: 7, publish_targets: {} };

const failure = (call: Promise<unknown>) =>
  call.then(
    () => null,
    (error: unknown) => error,
  );

const WORKING = makeArtifact({ id: "art-scene", kind: "image", language: null, size_bytes: 500 });

function finishedRun(daysAgo: number, overrides: Partial<Run> = {}, now = NOW): Run {
  return makeRun({
    id: `run-${daysAgo}`,
    status: "published",
    finished_at: new Date(now - daysAgo * DAY_MS).toISOString(),
    artifacts: [makeArtifact(), WORKING],
    ...overrides,
  });
}

describe("mock retention rules", () => {
  it.each(["queued", "running", "awaiting_review", "approved", "publishing"] as const)(
    "never touches a %s run",
    (status) => {
      expect(cleanupAction(finishedRun(400, { status }), NOW, POLICY)).toBeNull();
    },
  );

  it("removes working files first and the run at keep_runs_days, inclusive", () => {
    expect(cleanupAction(finishedRun(6.99), NOW, POLICY)).toBeNull();
    expect(cleanupAction(finishedRun(7), NOW, POLICY)).toBe("remove_intermediate");
    expect(cleanupAction(finishedRun(29.99), NOW, POLICY)).toBe("remove_intermediate");
    expect(cleanupAction(finishedRun(30), NOW, POLICY)).toBe("delete_run");
  });

  it("keeps everything with zero days", () => {
    const forever = { ...POLICY, keep_runs_days: 0, keep_intermediate_days: 0 };
    expect(cleanupAction(finishedRun(4000), NOW, forever)).toBeNull();
  });

  it("counts listed working files of any size and workspace bytes as work", () => {
    const finalOnly = finishedRun(10, { artifacts: [makeArtifact()] });
    const empty = finishedRun(10, { artifacts: [makeArtifact(), { ...WORKING, size_bytes: 0 }] });
    expect(hasIntermediateWork(finalOnly, 0)).toBe(false);
    expect(hasIntermediateWork(finalOnly, 5)).toBe(true);
    expect(hasIntermediateWork(empty, 0)).toBe(true);
    const storage = { ...db.state.storage, strays: [], workspace: { "run-10": 5 } };
    const items = cleanupItems([finalOnly], storage, NOW, POLICY);
    expect(items.map((item) => [item.action, item.bytes])).toEqual([["remove_intermediate", 5]]);
    expect(cleanupItems([finalOnly], { ...storage, workspace: {} }, NOW, POLICY)).toEqual([]);
  });

  it("protects pending and scheduled uploads", () => {
    const pending = finishedRun(40, { uploads: [makeUpload({ status: "pending" })] });
    expect(cleanupAction(pending, NOW, POLICY)).toBeNull();
    const later = new Date(NOW + DAY_MS).toISOString();
    const scheduled = finishedRun(40, { uploads: [makeUpload({ publish_at: later })] });
    expect(cleanupAction(scheduled, NOW, POLICY)).toBeNull();
    expect(cleanupAction(scheduled, NOW + DAY_MS, POLICY)).toBe("delete_run");
  });
});

describe("mock storage handlers", () => {
  it("reports disk use per automation with the stray folders", async () => {
    const report = await api.get<StorageReport>("/storage");
    expect(report.orphan_bytes).toBe(312_000_000);
    expect(report.automations.map((usage) => usage.automation_name)).toContain("Bedtime stories");
    expect(report.data_dir_bytes).toBe(
      report.final_bytes + report.intermediate_bytes + report.orphan_bytes + report.other_bytes,
    );
  });

  it("previews without removing and then cleans up", async () => {
    db.state.runs = [
      ...db.state.runs,
      finishedRun(45, {}, Date.now()),
      finishedRun(10, {}, Date.now()),
    ];
    const preview = await api.get<CleanupReport>("/storage/cleanup");
    expect(preview.dry_run).toBe(true);
    expect(preview.items.map((item) => [item.run_id, item.action])).toEqual([
      ["run-45", "delete_run"],
      ["run-3f9a2c", "remove_orphan"],
    ]);
    expect(db.state.runs.some((run) => run.id === "run-45")).toBe(true);

    const done = await api.post<CleanupReport>("/storage/cleanup");
    expect(done.dry_run).toBe(false);
    expect(done.total_bytes).toBe(preview.total_bytes);
    expect(db.state.runs.some((run) => run.id === "run-45")).toBe(false);
    expect(db.state.storage.strays).toEqual([]);
    expect((await api.post<CleanupReport>("/storage/cleanup")).items).toEqual([]);
  });

  it("strips working files and logs it", async () => {
    db.state.settings = { ...db.state.settings, keep_intermediate_days: 7 };
    db.state.runs = [finishedRun(10, {}, Date.now())];
    const done = await api.post<CleanupReport>("/storage/cleanup");
    expect(done.items[0]).toMatchObject({ action: "remove_intermediate", bytes: 500 });
    const [pruned] = db.state.runs;
    expect(pruned?.artifacts.map((artifact) => artifact.id)).toEqual([makeArtifact().id]);
    expect(pruned?.intermediate_removed_at).not.toBeNull();
    expect(pruned?.logs.at(-1)?.message).toContain("Cleanup removed working files");
  });
});

describe("mock settings handler", () => {
  const current = () => db.state.settings;

  it("saves new fields and ignores read-only ones", async () => {
    const saved = await api.put<AppSettings>("/settings", {
      ...current(),
      keep_intermediate_days: 3,
      data_dir: "/elsewhere",
    });
    expect(saved.keep_intermediate_days).toBe(3);
    expect(saved.data_dir).toBe(current().data_dir);
  });

  it.each([
    [{ keep_runs_days: -1 }, "keep_runs_days", "Input should be greater than or equal to 0"],
    [{ max_parallel_runs: 1.5 }, "max_parallel_runs", "Input should be a valid integer"],
    [
      { doctor_min_free_gb: -1 },
      "doctor_min_free_gb",
      "Input should be greater than or equal to 0",
    ],
    [{ timezone: "Mars/Base" }, "timezone", "unknown timezone 'Mars/Base'"],
    [
      { log_level: "loud" },
      "log_level",
      "Input should be 'debug', 'info', 'warning', 'error' or 'critical'",
    ],
  ])("rejects %j", async (patch, field, message) => {
    const error = await failure(api.put("/settings", { ...current(), ...patch }));
    expect(error).toMatchObject({ status: 400, fields: { [field]: message } });
  });

  it("changes only the sent fields, like the backend", async () => {
    const saved = await api.put<AppSettings>("/settings", { auto_cleanup_enabled: true });
    expect(saved).toMatchObject({ auto_cleanup_enabled: true, caption_track_name: "English" });
    expect(saved.keep_runs_days).toBe(30);
  });

  it("refuses to change a locked field but accepts it unchanged", async () => {
    const reason = current().locked.caption_track_name;
    const error = await failure(
      api.put("/settings", { ...current(), caption_track_name: "Tamil" }),
    );
    expect(error).toMatchObject({ status: 400, fields: { caption_track_name: reason } });
    await expect(api.put("/settings", current())).resolves.toMatchObject({
      caption_track_name: "English",
    });
  });
});

describe("mock retry after cleanup", () => {
  it("refuses a later stage and restarts from the first one", async () => {
    const pruned = makeRun({
      id: "run-pruned",
      status: "failed",
      intermediate_removed_at: db.now(),
    });
    db.state.runs = [pruned];
    const later = pruned.stages[2]?.stage_id;
    const error = await failure(api.post("/runs/run-pruned/retry", { from_stage: later }));
    expect(error).toMatchObject({ status: 409, code: "intermediate_files_removed" });
    const retried = await api.post<Run>("/runs/run-pruned/retry", {});
    expect(retried.stages.every((stage) => stage.status === "pending")).toBe(true);
    expect(retried.intermediate_removed_at).toBeNull();
  });
});
