from __future__ import annotations

import builtins
from collections.abc import Sequence

from automator.domain.pipeline import Pipeline


class StaticPipelineRegistry:
    def __init__(self, pipelines: Sequence[Pipeline]) -> None:
        self.pipelines = {pipeline.descriptor.type_id: pipeline for pipeline in pipelines}

    def list(self) -> builtins.list[Pipeline]:
        return builtins.list(self.pipelines.values())

    def get(self, type_id: str) -> Pipeline | None:
        return self.pipelines.get(type_id)
