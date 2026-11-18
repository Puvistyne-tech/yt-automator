import type { CleanupItem, CleanupReport, StorageReport } from "@/api/types";
import {
  cleanupResultMessage,
  itemTitle,
  policySummary,
  share,
  usageSummary,
} from "@/features/storage/model";

function item(overrides: Partial<CleanupItem> = {}): CleanupItem {
  return {
    run_id: "run-1",
    action: "delete_run",
    automation_id: "auto-1",
    automation_name: "Bedtime stories",
    status: "published",
    finished_at: null,
    bytes: 2_500_000,
    ...overrides,
  };
}

function report(items: CleanupItem[], days = { runs: 30, files: 0 }): CleanupReport {
  return {
    dry_run: false,
    keep_runs_days: days.runs,
    keep_intermediate_days: days.files,
    items,
    total_bytes: items.reduce((total, entry) => total + entry.bytes, 0),
  };
}

const STORAGE: StorageReport = {
  data_dir: "/d",
  data_dir_bytes: 1_000,
  free_bytes: 5_000_000,
  disk_bytes: 9_000_000,
  final_bytes: 300,
  intermediate_bytes: 100,
  orphan_bytes: 100,
  other_bytes: 500,
  automations: [],
};

describe("cleanup model", () => {
  it("names a run by its automation and a stray folder by its id", () => {
    expect(itemTitle(item())).toBe("Bedtime stories · run-1");
    expect(itemTitle(item({ action: "remove_orphan", automation_name: "" }))).toBe(
      "Folder run-1 (no run)",
    );
  });

  it("reports what a cleanup freed", () => {
    expect(cleanupResultMessage(report([]))).toBe("Nothing to clean up.");
    expect(cleanupResultMessage(report([item()]))).toBe("Cleanup freed 2.5 MB from 1 item.");
    expect(cleanupResultMessage(report([item(), item({ run_id: "run-2" })]))).toBe(
      "Cleanup freed 5.0 MB from 2 items.",
    );
  });

  it("explains the saved retention settings", () => {
    expect(policySummary(report([], { runs: 30, files: 0 }))).toContain(
      "finished runs older than 30 days go; working files are kept forever",
    );
    expect(policySummary(report([], { runs: 1, files: 1 }))).toContain(
      "finished runs older than 1 day go; working files older than 1 day go",
    );
    expect(policySummary(report([], { runs: 0, files: 7 }))).toContain(
      "finished runs are kept forever; working files older than 7 days go",
    );
  });
});

describe("storage model", () => {
  it("shares final outputs among run files and labels free space", () => {
    expect(usageSummary(STORAGE)).toEqual({
      runs_bytes: 500,
      working_bytes: 200,
      final_share: 60,
      free_label: "5.0 MB",
      stray_hint: "100 B in stray folders",
    });
    const clean = usageSummary({ ...STORAGE, free_bytes: null, orphan_bytes: 0 });
    expect(clean.free_label).toBe("Unknown");
    expect(clean.stray_hint).toBeUndefined();
  });

  it("never divides by zero", () => {
    expect(share(5, 0)).toBe(0);
  });
});
