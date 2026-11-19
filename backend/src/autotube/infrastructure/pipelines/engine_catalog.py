from __future__ import annotations

import builtins
from collections.abc import Sequence

from autotube.domain.pipeline_engine import PipelineEngine
from autotube.infrastructure.pipelines.pipeline_index import indexed_engines


class InstalledEngineCatalog:
    def __init__(self, engines: Sequence[PipelineEngine]) -> None:
        self.engines = indexed_engines(engines)

    def list(self) -> builtins.list[PipelineEngine]:
        return list(self.engines.values())

    def get(self, engine_id: str) -> PipelineEngine | None:
        return self.engines.get(engine_id)
