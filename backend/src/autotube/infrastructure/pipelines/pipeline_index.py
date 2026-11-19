from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_engine import PipelineEngine


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


def indexed_engines(engines: Sequence[PipelineEngine]) -> dict[str, PipelineEngine]:
    index: dict[str, PipelineEngine] = {}
    for engine in engines:
        if engine.engine_id in index:
            raise DuplicatePipelineError(
                f"two installed engines share the engine id {engine.engine_id!r}"
            )
        index[engine.engine_id] = engine
    return index
