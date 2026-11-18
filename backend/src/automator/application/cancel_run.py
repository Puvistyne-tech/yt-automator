from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_run
from automator.application.run_progress import RunProgress
from automator.domain.ports import RunQueue, RunRepository
from automator.domain.run_enums import RunStatus
from automator.domain.runs import Run


@dataclass(frozen=True)
class CancelRun:
    runs: RunRepository
    progress: RunProgress
    queue: RunQueue

    def execute(self, run_id: str) -> Run:
        run = require_run(self.runs, run_id)
        cancelled = self.progress.move(run, RunStatus.CANCELLED)
        self.queue.cancel(run.id)
        return cancelled
