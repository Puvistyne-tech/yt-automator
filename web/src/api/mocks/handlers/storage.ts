import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { cleanupItems, cleanupReport, runUsage, withoutIntermediate } from "@/api/mocks/retention";
import type { AutomationUsage, CleanupItem, CleanupReport, Run, StorageReport } from "@/api/types";

const MEGABYTE = 1_000_000;

function automationUsage(runs: Run[]): AutomationUsage[] {
  const grouped = new Map<string, AutomationUsage>();
  for (const run of runs) {
    const usage = runUsage(run);
    const entry = grouped.get(run.automation_id) ?? {
      automation_id: run.automation_id,
      automation_name: run.automation_name,
      runs: 0,
      final_bytes: 0,
      intermediate_bytes: 0,
    };
    grouped.set(run.automation_id, {
      ...entry,
      runs: entry.runs + 1,
      final_bytes: entry.final_bytes + usage.final_bytes,
      intermediate_bytes: entry.intermediate_bytes + usage.intermediate_bytes,
    });
  }
  const size = (usage: AutomationUsage) => usage.final_bytes + usage.intermediate_bytes;
  return [...grouped.values()].sort((a, b) => size(b) - size(a));
}

export function storageReport(): StorageReport {
  const { runs, storage, settings } = db.state;
  const automations = automationUsage(runs);
  const final = automations.reduce((total, usage) => total + usage.final_bytes, 0);
  const working = automations.reduce((total, usage) => total + usage.intermediate_bytes, 0);
  const strays = storage.strays.reduce((total, stray) => total + stray.bytes, 0);
  return {
    data_dir: settings.data_dir,
    data_dir_bytes: final + working + strays + storage.other_bytes,
    free_bytes: storage.free_bytes,
    disk_bytes: storage.disk_bytes,
    final_bytes: final,
    intermediate_bytes: working,
    orphan_bytes: strays,
    other_bytes: storage.other_bytes,
    automations,
  };
}

function preview(): CleanupItem[] {
  return cleanupItems(db.state.runs, db.state.storage, Date.now(), db.state.settings);
}

function apply(item: CleanupItem): void {
  const state = db.state;
  if (item.action === "remove_orphan") {
    state.storage = {
      ...state.storage,
      strays: state.storage.strays.filter((s) => s.run_id !== item.run_id),
    };
    return;
  }
  if (item.action === "delete_run") {
    state.runs = state.runs.filter((run) => run.id !== item.run_id);
    return;
  }
  const message = `Cleanup removed working files (${(item.bytes / MEGABYTE).toFixed(1)} MB)`;
  state.runs = state.runs.map((run) =>
    run.id === item.run_id ? withoutIntermediate(run, db.now(), message) : run,
  );
}

export function cleanUp(): CleanupReport {
  const items = preview();
  items.forEach(apply);
  return cleanupReport(items, db.state.settings, false);
}

export const storageHandlers = [
  http.get("/api/storage", () => HttpResponse.json(storageReport())),
  http.get("/api/storage/cleanup", () =>
    HttpResponse.json(cleanupReport(preview(), db.state.settings, true)),
  ),
  http.post("/api/storage/cleanup", () => HttpResponse.json(cleanUp())),
];
