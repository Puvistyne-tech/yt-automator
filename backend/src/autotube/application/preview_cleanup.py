from __future__ import annotations

from dataclasses import dataclass

from autotube.application.cleanup_planner import CleanupPlanner
from autotube.domain.retention import CleanupReport, cleanup_report


@dataclass(frozen=True)
class PreviewCleanup:
    planner: CleanupPlanner

    def execute(self) -> CleanupReport:
        plan = self.planner.plan()
        return cleanup_report(plan.items, plan.policy, dry_run=True)
