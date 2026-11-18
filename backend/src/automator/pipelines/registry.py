from __future__ import annotations

import builtins
from collections.abc import Callable, Sequence
from importlib import import_module
from typing import cast

from automator.domain.pipeline import Pipeline
from automator.domain.ports import PipelineRegistry

INSTALLED_PIPELINES: tuple[str, ...] = ("automator.pipelines.kids_story.plugin:KidsStoryPipeline",)


class StaticPipelineRegistry:
    def __init__(self, pipelines: Sequence[Pipeline]) -> None:
        self.pipelines = {pipeline.descriptor.type_id: pipeline for pipeline in pipelines}

    def list(self) -> builtins.list[Pipeline]:
        return builtins.list(self.pipelines.values())

    def get(self, type_id: str) -> Pipeline | None:
        return self.pipelines.get(type_id)


def load_pipeline(reference: str) -> Pipeline:
    module_name, _, factory_name = reference.partition(":")
    factory = cast(Callable[[], Pipeline], getattr(import_module(module_name), factory_name))
    return factory()


def build_pipeline_registry() -> PipelineRegistry:
    return StaticPipelineRegistry([load_pipeline(reference) for reference in INSTALLED_PIPELINES])
