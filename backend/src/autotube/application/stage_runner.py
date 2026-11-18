from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial

from autotube.application.run_progress import RunProgress
from autotube.application.run_recorder import RunRecorder
from autotube.domain.pipeline import Stage, StageContext, StageOutcome
from autotube.domain.ports import ArtifactStore, Clock, IdGenerator
from autotube.domain.run_enums import RunStatus, StageStatus
from autotube.domain.run_parts import Artifact, StageRun
from autotube.domain.run_state import accepts_stage_results
from autotube.domain.runs import Run
from autotube.shared.errors import describe_error

ContextFactory = Callable[[Run], StageContext]


def is_running(run: Run) -> bool:
    return run.status is RunStatus.RUNNING


def accepts_results(run: Run) -> bool:
    return accepts_stage_results(run.status)


def seen_and_accepted(seen: list[Run], run: Run) -> bool:
    seen.append(run)
    return accepts_results(run)


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
        recorded = self.recorder.stage(run.id, started, is_running)
        if recorded is None:
            return self.progress.synced(run)
        try:
            outcome = stage.run(self.stage_context(recorded, stage_id, context_for))
            saved = self.saved_artifacts(run.id, stage_id, outcome)
        except Exception as error:
            return self.failed(recorded, started, error)
        return self.completed(recorded, started, outcome, saved)

    def stage_context(self, run: Run, stage_id: str, context_for: ContextFactory) -> StageContext:
        log = partial(self.recorder.log, run.id, stage_id=stage_id)
        return replace(context_for(run), log=log)

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
        seen: list[Run] = []
        recorded = self.recorder.stage(run.id, stage, partial(seen_and_accepted, seen))
        if not seen:
            self.store.delete_run(run.id)
        if recorded is None or recorded.status is not RunStatus.RUNNING:
            return self.progress.synced(run)
        failure = f"stage {stage.stage_id} failed: {message}"
        return self.progress.fail(recorded, failure) or self.progress.synced(run)

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
        seen: list[Run] = []
        recorded = self.recorder.stage(run.id, stage, partial(seen_and_accepted, seen), saved)
        if recorded is None:
            self.discard_unrecorded(run.id, seen, saved)
            return self.progress.synced(run)
        return recorded

    def discard_unrecorded(self, run_id: str, seen: list[Run], saved: tuple[Artifact, ...]) -> None:
        if not seen:
            self.store.delete_run(run_id)
            return
        kept = {artifact.filename for artifact in seen[-1].artifacts}
        for artifact in saved:
            if artifact.filename not in kept:
                self.store.discard(run_id, artifact)
