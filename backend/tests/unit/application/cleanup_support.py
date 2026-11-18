from __future__ import annotations

from typing import Any

from automator.domain.run_enums import ArtifactKind, RunStatus
from automator.domain.run_parts import Artifact
from automator.domain.runs import Run
from automator.domain.settings import AppSettingsInput
from tests.fixtures.fake_runtime import START
from tests.fixtures.fake_storage import artifact_path, workspace_path
from tests.fixtures.harness import Harness
from tests.unit.infrastructure.records import run

VIDEO_BYTES = 100
IMAGE_BYTES = 30
WORKSPACE_BYTES = 20


def keep(harness: Harness, runs: int = 30, intermediate: int = 7) -> None:
    harness.app_settings.stored = AppSettingsInput(
        keep_runs_days=runs, keep_intermediate_days=intermediate
    )


def artifact(artifact_id: str, kind: ArtifactKind, language: str | None) -> Artifact:
    return Artifact(
        id=artifact_id,
        kind=kind,
        stage_id="script",
        language=language,
        filename=f"{artifact_id}.bin",
        media_type="application/octet-stream",
        size_bytes=1,
    )


def stored_run(
    harness: Harness, run_id: str, status: RunStatus = RunStatus.PUBLISHED, **changes: Any
) -> Run:
    video = artifact(f"{run_id}-v", ArtifactKind.VIDEO, "en")
    image = artifact(f"{run_id}-i", ArtifactKind.IMAGE, None)
    fields: dict[str, Any] = {"finished_at": START, "artifacts": (video, image)} | changes
    saved = run(run_id, status=status, **fields)
    harness.runs.save(saved)
    harness.files.put(run_id, artifact_path(video.id), VIDEO_BYTES)
    harness.files.put(run_id, artifact_path(image.id), IMAGE_BYTES)
    harness.files.put(run_id, workspace_path("scene.png"), WORKSPACE_BYTES)
    return saved


def orphan(harness: Harness, run_id: str = "orphan-1", size: int = 9) -> None:
    harness.files.put(run_id, workspace_path("left.bin"), size)


def after_days(harness: Harness, days: float) -> None:
    harness.clock.current = START
    harness.clock.advance(days=days)
