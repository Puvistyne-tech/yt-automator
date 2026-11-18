from __future__ import annotations

from dataclasses import dataclass

from automator.domain.pipeline_descriptors import PipelineDescriptor
from automator.domain.ports import PipelineRegistry


@dataclass(frozen=True)
class ListPipelines:
    pipelines: PipelineRegistry

    def execute(self) -> list[PipelineDescriptor]:
        descriptors = [pipeline.descriptor for pipeline in self.pipelines.list()]
        return sorted(descriptors, key=lambda descriptor: descriptor.name.casefold())
