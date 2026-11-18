from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from automator.application.lookups import require
from automator.application.run_recorder import RunRecorder
from automator.domain.ports import Clock, RunRepository
from automator.domain.run_enums import RunStatus
from automator.domain.run_state import transition
from automator.domain.runs import Run

Prepare = Callable[[Run], Run]


def keep(run: Run) -> Run:
    return run


@dataclass(frozen=True)
class RunProgress:
    runs: RunRepository
    recorder: RunRecorder
    clock: Clock

    def synced(self, run: Run) -> Run:
        latest = self.runs.get(run.id)
        if latest is None:
            return run.model_copy(update={"status": RunStatus.CANCELLED})
        return latest

    def transitioned(
        self, stored: Run, status: RunStatus, error: str | None, prepare: Prepare
    ) -> Run:
        return transition(prepare(stored), status, self.clock.now(), error)

    def move(
        self,
        run_id: str,
        status: RunStatus,
        error: str | None = None,
        prepare: Prepare = keep,
    ) -> Run:
        saved = self.recorder.status(
            run_id, lambda stored: self.transitioned(stored, status, error, prepare)
        )
        return require(saved, "run", run_id)

    def advance(
        self,
        run: Run,
        status: RunStatus,
        error: str | None = None,
        updates: Mapping[str, object] | None = None,
    ) -> Run | None:
        def change(stored: Run) -> Run | None:
            if stored.status is not run.status:
                return None
            prepared = stored.model_copy(update=dict(updates or {}))
            return transition(prepared, status, self.clock.now(), error)

        return self.recorder.status(run.id, change)

    def fail(self, run: Run, error: str) -> Run | None:
        return self.advance(run, RunStatus.FAILED, error)
