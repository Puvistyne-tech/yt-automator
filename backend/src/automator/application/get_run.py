from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require
from automator.domain.ports import RunRepository
from automator.domain.runs import Run


@dataclass(frozen=True)
class GetRun:
    runs: RunRepository

    def execute(self, run_id: str) -> Run:
        return require(self.runs.get(run_id), "run", run_id)
