from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require_run
from autotube.application.run_progress import RunProgress
from autotube.domain.ports import RunQueue, RunRepository
from autotube.domain.run_enums import RunStatus
from autotube.domain.runs import Run


@dataclass(frozen=True)
class CancelRun:
    runs: RunRepository
    progress: RunProgress
    queue: RunQueue

    def execute(self, run_id: str) -> Run:
        run = require_run(self.runs, run_id)
        cancelled = self.progress.move(run.id, RunStatus.CANCELLED)
        self.queue.cancel(run.id)
        return cancelled
