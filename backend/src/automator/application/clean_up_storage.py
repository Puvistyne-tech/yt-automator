from __future__ import annotations

import logging
from dataclasses import dataclass

from automator.application.cleanup_planner import CleanupPlan, CleanupPlanner
from automator.application.run_recorder import RunRecorder
from automator.domain.ports import RunFileStore, RunRepository
from automator.domain.retention import (
    CleanupAction,
    CleanupItem,
    CleanupReport,
    cleanup_action,
    cleanup_report,
    final_artifact_ids,
    megabytes,
    without_intermediate,
    working_files_removed_message,
)
from automator.domain.runs import Run
from automator.shared.errors import describe_error

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanUpStorage:
    planner: CleanupPlanner
    runs: RunRepository
    files: RunFileStore
    recorder: RunRecorder

    def execute(self) -> CleanupReport:
        plan = self.planner.plan()
        attempts = (self.attempt(plan, item) for item in plan.items)
        done = [item for item in attempts if item is not None]
        report = cleanup_report(done, plan.policy, dry_run=False)
        logger.info("cleanup freed %s across %d items", megabytes(report.total_bytes), len(done))
        return report

    def attempt(self, plan: CleanupPlan, item: CleanupItem) -> CleanupItem | None:
        try:
            freed = self.apply(plan, item)
        except Exception as error:
            logger.warning("cleanup of %s failed: %s", item.run_id, describe_error(error))
            return None
        return item.model_copy(update={"bytes": freed}) if freed is not None else None

    def apply(self, plan: CleanupPlan, item: CleanupItem) -> int | None:
        if item.action is CleanupAction.DELETE_RUN:
            return self.delete_run(plan, item.run_id)
        if item.action is CleanupAction.REMOVE_INTERMEDIATE:
            return self.remove_intermediate(plan, item.run_id)
        return self.remove_orphan(item.run_id)

    def still(self, plan: CleanupPlan, action: CleanupAction, run: Run | None) -> bool:
        return run is not None and cleanup_action(run, plan.now, plan.policy) is action

    def still_pruned(self, plan: CleanupPlan, run_id: str) -> Run | None:
        current = self.runs.get(run_id)
        pruned = current is not None and current.intermediate_removed_at is not None
        keep = pruned and self.still(plan, CleanupAction.REMOVE_INTERMEDIATE, current)
        return current if keep else None

    def delete_run(self, plan: CleanupPlan, run_id: str) -> int | None:
        expired = self.runs.delete_if(
            run_id, lambda run: self.still(plan, CleanupAction.DELETE_RUN, run)
        )
        if expired is None:
            return None
        freed = self.files.delete_run(run_id)
        logger.info("deleted run %s of %s, %s", run_id, expired.automation_name, megabytes(freed))
        return freed

    def mark_pruned(self, plan: CleanupPlan, run_id: str) -> Run | None:
        def change(run: Run) -> Run | None:
            if not self.still(plan, CleanupAction.REMOVE_INTERMEDIATE, run):
                return None
            return without_intermediate(run, plan.now)

        return self.runs.update(run_id, change)

    def remove_intermediate(self, plan: CleanupPlan, run_id: str) -> int | None:
        if self.mark_pruned(plan, run_id) is None:
            return None
        pruned = self.still_pruned(plan, run_id)
        if pruned is None:
            return None
        freed = self.files.remove_intermediate(run_id, final_artifact_ids(pruned))
        self.recorder.log(run_id, working_files_removed_message(freed))
        logger.info("removed working files of run %s, %s", run_id, megabytes(freed))
        return freed

    def remove_orphan(self, run_id: str) -> int | None:
        if self.runs.get(run_id) is not None:
            return None
        freed = self.files.delete_run(run_id)
        logger.info("removed folder %s with no run, %s", run_id, megabytes(freed))
        return freed
