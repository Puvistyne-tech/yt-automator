from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from automator.domain.model_base import JsonObject
from automator.domain.ports import Clock, RunEvents, RunRepository
from automator.domain.run_enums import LogLevel, RunEventKind
from automator.domain.run_parts import Artifact, RunLog, StageRun, Upload
from automator.domain.runs import Run, RunEvent


@dataclass(frozen=True)
class RunRecorder:
    runs: RunRepository
    events: RunEvents
    clock: Clock

    def emit(self, run_id: str, kind: RunEventKind, payload: JsonObject) -> None:
        self.events.publish(
            RunEvent(run_id=run_id, kind=kind, at=self.clock.now(), payload=payload)
        )

    def _save_and_emit(
        self, run: Run, kind: RunEventKind, parts: Sequence[StageRun | Artifact | Upload]
    ) -> Run:
        self.runs.save(run)
        for part in parts:
            self.emit(run.id, kind, part.model_dump(mode="json"))
        return run

    def status(self, run: Run) -> Run:
        self.runs.save(run)
        payload: JsonObject = {"status": run.status.value, "error": run.error}
        self.emit(run.id, RunEventKind.STATUS, payload)
        return run

    def stage(self, run: Run, stage: StageRun) -> Run:
        updated = run.model_copy(
            update={
                "stages": tuple(stage if s.stage_id == stage.stage_id else s for s in run.stages)
            }
        )
        return self._save_and_emit(updated, RunEventKind.STAGE, (stage,))

    def artifacts(self, run: Run, added: tuple[Artifact, ...]) -> Run:
        updated = run.model_copy(update={"artifacts": run.artifacts + added})
        return self._save_and_emit(updated, RunEventKind.ARTIFACT, added)

    def upload(self, run: Run, index: int, upload: Upload) -> Run:
        uploads = run.uploads[:index] + (upload,) + run.uploads[index + 1 :]
        updated = run.model_copy(update={"uploads": uploads})
        return self._save_and_emit(updated, RunEventKind.UPLOAD, (upload,))

    def log(
        self,
        run_id: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        stage_id: str | None = None,
    ) -> None:
        entry = RunLog(at=self.clock.now(), level=level, stage_id=stage_id, message=message)
        stored = self.runs.get(run_id)
        if stored is not None:
            self.runs.save(stored.model_copy(update={"logs": (*stored.logs, entry)}))
        self.emit(run_id, RunEventKind.LOG, entry.model_dump(mode="json", exclude={"at"}))
