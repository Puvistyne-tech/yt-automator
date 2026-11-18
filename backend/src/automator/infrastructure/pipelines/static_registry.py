from __future__ import annotations

import builtins
from collections.abc import Sequence

from automator.domain.pipeline import Pipeline


class DuplicatePipelineError(ValueError):
    pass


def indexed(pipelines: Sequence[Pipeline]) -> dict[str, Pipeline]:
    index: dict[str, Pipeline] = {}
    for pipeline in pipelines:
        type_id = pipeline.descriptor.type_id
        if type_id in index:
            raise DuplicatePipelineError(f"two installed pipelines share the type id {type_id!r}")
        index[type_id] = pipeline
    return index


class StaticPipelineRegistry:
    def __init__(self, pipelines: Sequence[Pipeline]) -> None:
        self.pipelines = indexed(pipelines)

    def list(self) -> builtins.list[Pipeline]:
        return builtins.list(self.pipelines.values())

    def get(self, type_id: str) -> Pipeline | None:
        return self.pipelines.get(type_id)
