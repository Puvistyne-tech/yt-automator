from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_run
from automator.application.run_progress import RunProgress
from automator.domain.ports import ArtifactStore, RunQueue, RunRepository
from automator.domain.run_edits import removed_artifacts
from automator.domain.run_enums import RunStatus, StageStatus
from automator.domain.run_parts import StageRun
from automator.domain.run_state import ensure_transition
from automator.domain.runs import Run
from automator.shared.errors import ValidationFailed


def retry_start(run: Run, from_stage: str | None) -> int:
    stage_ids = [stage.stage_id for stage in run.stages]
    if from_stage is not None:
        if from_stage not in stage_ids:
            raise ValidationFailed({"from_stage": f"run has no stage {from_stage!r}"})
        return stage_ids.index(from_stage)
    unfinished = [i for i, stage in enumerate(run.stages) if stage.status is not StageStatus.DONE]
    return unfinished[0] if unfinished else 0


def retry_reset(from_stage: str | None, run: Run) -> Run:
    ensure_transition(run, RunStatus.QUEUED)
    start = retry_start(run, from_stage)
    reset_ids = {stage.stage_id for stage in run.stages[start:]}
    return run.model_copy(
        update={
            "stages": run.stages[:start]
            + tuple(StageRun(stage_id=s.stage_id, title=s.title) for s in run.stages[start:]),
            "artifacts": tuple(a for a in run.artifacts if a.stage_id not in reset_ids),
            "score": None,
            "score_details": (),
            "review": None,
            "uploads": (),
        }
    )


@dataclass(frozen=True)
class RetryRun:
    runs: RunRepository
    store: ArtifactStore
    progress: RunProgress
    queue: RunQueue

    def execute(self, run_id: str, from_stage: str | None = None) -> Run:
        require_run(self.runs, run_id)
        before: list[Run] = []

        def prepare(stored: Run) -> Run:
            before.append(stored)
            return retry_reset(from_stage, stored)

        queued = self.progress.move(run_id, RunStatus.QUEUED, prepare=prepare)
        for artifact in removed_artifacts(before[-1], queued):
            self.store.discard(run_id, artifact)
        self.queue.enqueue(queued.id)
        return queued
