from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_run
from automator.domain.deletion_rules import ensure_run_deletable
from automator.domain.ports import ArtifactStore, RunRepository


@dataclass(frozen=True)
class DeleteRun:
    runs: RunRepository
    store: ArtifactStore

    def execute(self, run_id: str) -> None:
        run = require_run(self.runs, run_id)
        ensure_run_deletable(run)
        self.runs.delete(run.id)
        self.store.delete_run(run.id)
