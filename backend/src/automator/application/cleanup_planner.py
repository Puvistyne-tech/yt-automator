from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from automator.domain.ports import (
    AppSettingsRepository,
    AutomationRepository,
    Clock,
    RunFileStore,
    RunRepository,
)
from automator.domain.retention import (
    CleanupAction,
    CleanupItem,
    RetentionPolicy,
    cleanup_action,
    final_artifact_ids,
    has_intermediate_work,
    retention_policy,
    run_item,
)
from automator.domain.runs import Run, RunQuery
from automator.domain.upload_hold import publish_targets

NO_FINALS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CleanupPlan:
    now: datetime
    policy: RetentionPolicy
    items: tuple[CleanupItem, ...]


@dataclass(frozen=True)
class RunSnapshot:
    runs: tuple[Run, ...]
    orphan_ids: tuple[str, ...]


@dataclass(frozen=True)
class CleanupPlanner:
    runs: RunRepository
    files: RunFileStore
    settings: AppSettingsRepository
    clock: Clock
    automations: AutomationRepository

    def snapshot(self) -> RunSnapshot:
        on_disk = self.files.run_ids()
        runs = tuple(self.runs.list(RunQuery()))
        known = {run.id for run in runs}
        return RunSnapshot(runs, tuple(sorted(on_disk - known)))

    def policy(self) -> RetentionPolicy:
        targets = publish_targets(self.automations.list())
        return retention_policy(self.settings.get(), targets)

    def plan(self) -> CleanupPlan:
        now, policy = self.clock.now(), self.policy()
        snapshot = self.snapshot()
        found = (self.run_item(run, now, policy) for run in snapshot.runs)
        orphans = (self.orphan_item(run_id) for run_id in snapshot.orphan_ids)
        items = tuple(item for item in (*found, *orphans) if item is not None)
        return CleanupPlan(now, policy, items)

    def run_item(self, run: Run, now: datetime, policy: RetentionPolicy) -> CleanupItem | None:
        action = cleanup_action(run, now, policy)
        if action is None:
            return None
        usage = self.files.usage(run.id, final_artifact_ids(run))
        if action is CleanupAction.DELETE_RUN:
            return run_item(run, action, usage.total_bytes)
        if not has_intermediate_work(run, usage.intermediate_bytes):
            return None
        return run_item(run, action, usage.intermediate_bytes)

    def orphan_item(self, run_id: str) -> CleanupItem:
        size = self.files.usage(run_id, NO_FINALS).total_bytes
        return CleanupItem(run_id=run_id, action=CleanupAction.REMOVE_ORPHAN, bytes=size)
