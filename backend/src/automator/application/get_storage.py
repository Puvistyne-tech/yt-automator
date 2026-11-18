from __future__ import annotations

from dataclasses import dataclass

from automator.application.cleanup_planner import NO_FINALS, CleanupPlanner
from automator.domain.ports import RunFileStore
from automator.domain.retention import final_artifact_ids
from automator.domain.storage import RunUsage, StorageReport, storage_report


@dataclass(frozen=True)
class GetStorage:
    planner: CleanupPlanner
    files: RunFileStore

    def execute(self) -> StorageReport:
        snapshot = self.planner.snapshot()
        usages: list[RunUsage] = [
            (run, self.files.usage(run.id, final_artifact_ids(run))) for run in snapshot.runs
        ]
        orphans = sum(
            self.files.usage(run_id, NO_FINALS).total_bytes for run_id in snapshot.orphan_ids
        )
        return storage_report(self.files.disk(), usages, orphans)
