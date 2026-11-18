from __future__ import annotations

from dataclasses import dataclass

from automator.domain.model_base import JsonObject
from automator.domain.ports import Clock, RunEvents, RunRepository
from automator.domain.run_enums import RunEventKind
from automator.domain.run_parts import Artifact, StageRun, Upload
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
        self.runs.save(updated)
        self.emit(run.id, RunEventKind.STAGE, stage.model_dump(mode="json"))
        return updated

    def artifacts(self, run: Run, added: tuple[Artifact, ...]) -> Run:
        updated = run.model_copy(update={"artifacts": run.artifacts + added})
        self.runs.save(updated)
        for artifact in added:
            self.emit(run.id, RunEventKind.ARTIFACT, artifact.model_dump(mode="json"))
        return updated

    def upload(self, run: Run, index: int, upload: Upload) -> Run:
        uploads = run.uploads[:index] + (upload,) + run.uploads[index + 1 :]
        updated = run.model_copy(update={"uploads": uploads})
        self.runs.save(updated)
        self.emit(run.id, RunEventKind.UPLOAD, upload.model_dump(mode="json"))
        return updated

    def log(self, run_id: str, message: str) -> None:
        self.emit(run_id, RunEventKind.LOG, {"message": message})
