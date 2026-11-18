from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.ports import PipelineRegistry


@dataclass(frozen=True)
class ListPipelines:
    pipelines: PipelineRegistry

    def execute(self) -> list[PipelineDescriptor]:
        descriptors = [pipeline.descriptor for pipeline in self.pipelines.list()]
        return sorted(descriptors, key=lambda descriptor: descriptor.name.casefold())
