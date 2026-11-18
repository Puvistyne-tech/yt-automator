from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.ports import RunRepository
from autotube.domain.runs import Run, RunQuery


@dataclass(frozen=True)
class ListRuns:
    runs: RunRepository
    default_limit: int = 50

    def execute(self, query: RunQuery | None = None) -> list[Run]:
        query = query or RunQuery()
        if query.limit is None:
            query = query.model_copy(update={"limit": self.default_limit})
        return sorted(self.runs.list(query), key=lambda run: run.created_at, reverse=True)
