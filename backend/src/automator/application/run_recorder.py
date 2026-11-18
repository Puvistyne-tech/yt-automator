from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from automator.application.lookups import require
from automator.domain.model_base import JsonObject
from automator.domain.ports import Clock, RunChange, RunEvents, RunRepository
from automator.domain.run_edits import with_artifacts, with_stage, with_upload
from automator.domain.run_enums import LogLevel, RunEventKind
from automator.domain.run_parts import Artifact, RunLog, RunLogPolicy, StageRun, Upload
from automator.domain.runs import Run, RunEvent

RunCheck = Callable[[Run], bool]


@dataclass(frozen=True)
class RunRecorder:
    runs: RunRepository
    events: RunEvents
    clock: Clock
    log_policy: RunLogPolicy = field(default_factory=RunLogPolicy)

    def emit(self, run_id: str, kind: RunEventKind, payload: JsonObject) -> None:
        self.events.publish(
            RunEvent(run_id=run_id, kind=kind, at=self.clock.now(), payload=payload)
        )

    def emit_parts(
        self, run_id: str, kind: RunEventKind, parts: Sequence[StageRun | Artifact | Upload]
    ) -> None:
        for part in parts:
            self.emit(run_id, kind, part.model_dump(mode="json"))

    def emit_status(self, run: Run) -> Run:
        payload: JsonObject = {"status": run.status.value, "error": run.error}
        self.emit(run.id, RunEventKind.STATUS, payload)
        return run

    def created(self, run: Run) -> Run:
        self.runs.save(run)
        return self.emit_status(run)

    def status(self, run_id: str, change: RunChange) -> Run | None:
        saved = self.runs.update(run_id, change)
        return self.emit_status(saved) if saved is not None else None

    def stage(
        self, run_id: str, stage: StageRun, accepts: RunCheck, added: tuple[Artifact, ...] = ()
    ) -> Run | None:
        def change(stored: Run) -> Run | None:
            if not accepts(stored):
                return None
            return with_stage(with_artifacts(stored, added), stage)

        saved = self.runs.update(run_id, change)
        if saved is not None:
            self.emit_parts(run_id, RunEventKind.ARTIFACT, added)
            self.emit_parts(run_id, RunEventKind.STAGE, (stage,))
        return saved

    def upload(self, run_id: str, index: int, upload: Upload) -> Run:
        saved = require(
            self.runs.update(run_id, lambda stored: with_upload(stored, index, upload)),
            "run",
            run_id,
        )
        self.emit_parts(run_id, RunEventKind.UPLOAD, (upload,))
        return saved

    def log(
        self,
        run_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        stage_id: str | None = None,
    ) -> None:
        entry = RunLog(at=self.clock.now(), level=level, stage_id=stage_id, message=message)
        if self.runs.update(run_id, lambda stored: self.logged(stored, entry)) is None:
            return
        self.emit(run_id, RunEventKind.LOG, entry.model_dump(mode="json", exclude={"at"}))

    def logged(self, stored: Run, entry: RunLog) -> Run:
        return stored.model_copy(update={"logs": self.log_policy.appended(stored.logs, entry)})
