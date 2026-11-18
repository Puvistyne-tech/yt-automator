from __future__ import annotations

from autotube.domain.run_parts import Artifact, StageRun, Upload
from autotube.domain.runs import Run


def with_stage(run: Run, stage: StageRun) -> Run:
    if run.stage(stage.stage_id) is None:
        return run.model_copy(update={"stages": (*run.stages, stage)})
    stages = tuple(stage if s.stage_id == stage.stage_id else s for s in run.stages)
    return run.model_copy(update={"stages": stages})


def with_artifacts(run: Run, added: tuple[Artifact, ...]) -> Run:
    return run.model_copy(update={"artifacts": run.artifacts + added})


def with_upload(run: Run, index: int, upload: Upload) -> Run:
    uploads = run.uploads[:index] + (upload,) + run.uploads[index + 1 :]
    return run.model_copy(update={"uploads": uploads})


def removed_artifacts(before: Run, after: Run) -> tuple[Artifact, ...]:
    kept = {artifact.id for artifact in after.artifacts}
    return tuple(artifact for artifact in before.artifacts if artifact.id not in kept)
