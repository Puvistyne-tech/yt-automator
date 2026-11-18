from __future__ import annotations

from typing import Any

from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact

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
