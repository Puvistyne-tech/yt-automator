from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from automator.application.run_progress import RunProgress
from automator.application.run_recorder import RunRecorder
from automator.domain.pipeline import Stage, StageContext, StageOutcome
from automator.domain.ports import ArtifactStore, Clock, IdGenerator
from automator.domain.run_enums import RunStatus, StageStatus
from automator.domain.run_parts import Artifact, StageRun
from automator.domain.runs import Run
from automator.shared.errors import describe_error

ContextFactory = Callable[[Run], StageContext]


@dataclass(frozen=True)
class StageRunner:
    store: ArtifactStore
    recorder: RunRecorder
    progress: RunProgress
    ids: IdGenerator
    clock: Clock

    def run(self, run: Run, stage: Stage, context_for: ContextFactory) -> Run:
        stage_id = stage.descriptor.id
        record = run.stage(stage_id) or StageRun(stage_id=stage_id, title=stage.descriptor.title)
        if record.status is StageStatus.DONE:
            return run
        started = record.model_copy(
            update={
                "status": StageStatus.RUNNING,
                "provider": "",
                "message": "",
                "started_at": self.clock.now(),
                "finished_at": None,
            }
        )
        run = self.recorder.stage(self.with_stage(run, started), started)
        try:
            outcome = stage.run(context_for(run))
            saved = self.saved_artifacts(run.id, stage_id, outcome)
        except Exception as error:
            return self.failed(run, started, error)
        return self.completed(run, started, outcome, saved)

    def with_stage(self, run: Run, stage: StageRun) -> Run:
        if run.stage(stage.stage_id) is not None:
            return run
        return run.model_copy(update={"stages": (*run.stages, stage)})

    def saved_artifacts(
        self, run_id: str, stage_id: str, outcome: StageOutcome
    ) -> tuple[Artifact, ...]:
        return tuple(
            self.store.save(run_id, self.ids.new(), stage_id, new) for new in outcome.artifacts
        )

    def failed(self, run: Run, started: StageRun, error: Exception) -> Run:
        message = describe_error(error)
        stage = started.model_copy(
            update={
                "status": StageStatus.FAILED,
                "message": message,
                "finished_at": self.clock.now(),
            }
        )
        run = self.recorder.stage(self.progress.synced(run), stage)
        if run.status is not RunStatus.RUNNING:
            return run
        return self.progress.fail(run, f"stage {stage.stage_id} failed: {message}")

    def completed(
        self, run: Run, started: StageRun, outcome: StageOutcome, saved: tuple[Artifact, ...]
    ) -> Run:
        stage = started.model_copy(
            update={
                "status": StageStatus.DONE,
                "provider": outcome.provider,
                "message": outcome.message,
                "finished_at": self.clock.now(),
            }
        )
        run = self.progress.synced(run)
        return self.recorder.stage(self.recorder.artifacts(run, saved), stage)
