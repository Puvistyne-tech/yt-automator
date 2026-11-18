from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.ports import PipelineRegistry


@dataclass(frozen=True)
class GetPipeline:
    pipelines: PipelineRegistry

    def execute(self, type_id: str) -> PipelineDescriptor:
        return require(self.pipelines.get(type_id), "pipeline", type_id).descriptor
