from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automator.application.lookups import require
from automator.domain.ports import ArtifactStore, RunRepository
from automator.domain.run_parts import Artifact


@dataclass(frozen=True)
class OpenRunArtifact:
    runs: RunRepository
    store: ArtifactStore

    def execute(self, run_id: str, artifact_id: str) -> tuple[Artifact, Path]:
        run = require(self.runs.get(run_id), "run", run_id)
        found = next((a for a in run.artifacts if a.id == artifact_id), None)
        artifact = require(found, "artifact", artifact_id)
        return artifact, self.store.open(run.id, artifact)
