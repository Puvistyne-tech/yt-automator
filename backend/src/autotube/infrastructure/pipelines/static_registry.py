from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.pipeline import Pipeline


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
