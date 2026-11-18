from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from automator.domain.run_enums import ArtifactKind, RunStatus
from automator.domain.run_parts import Artifact, Upload
from automator.domain.runs import Run
from tests.fixtures.fake_runtime import START
from tests.unit.infrastructure.records import run

FINISHED = START

LEGACY_PAYLOAD: dict[str, Any] = {
    "timezone": "Asia/Kolkata",
    "max_parallel_runs": 2,
    "keep_runs_days": 7,
    "data_dir": "",
}


def artifact(artifact_id: str, kind: ArtifactKind, language: str | None = "en") -> Artifact:
    return Artifact(
        id=artifact_id,
        kind=kind,
        stage_id="script",
        language=language,
        filename=f"{artifact_id}.bin",
        media_type="application/octet-stream",
        size_bytes=1,
    )


def upload(**changes: Any) -> Upload:
    base = Upload(target_id="t", channel_id="c", language="en", variant="v")
    return base.model_copy(update=changes)


def finished(status: RunStatus = RunStatus.PUBLISHED, **changes: Any) -> Run:
    return run("r1", status=status, finished_at=FINISHED, **changes)


def days_later(days: float) -> datetime:
    return FINISHED + timedelta(days=days)
