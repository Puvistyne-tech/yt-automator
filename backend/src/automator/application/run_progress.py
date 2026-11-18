from __future__ import annotations

from dataclasses import dataclass

from automator.application.run_recorder import RunRecorder
from automator.domain.ports import Clock, RunRepository
from automator.domain.run_enums import RunStatus
from automator.domain.run_state import transition
from automator.domain.runs import Run


@dataclass(frozen=True)
class RunProgress:
    runs: RunRepository
    recorder: RunRecorder
    clock: Clock

    def synced(self, run: Run) -> Run:
        latest = self.runs.get(run.id)
        if latest is None or latest.status is run.status:
            return run
        return run.model_copy(
            update={
                "status": latest.status,
                "error": latest.error,
                "finished_at": latest.finished_at,
            }
        )

    def move(self, run: Run, status: RunStatus, error: str | None = None) -> Run:
        return self.recorder.status(transition(run, status, self.clock.now(), error))

    def fail(self, run: Run, error: str) -> Run:
        return self.move(run, RunStatus.FAILED, error)
