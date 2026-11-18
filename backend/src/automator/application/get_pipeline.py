from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require
from automator.domain.pipeline_descriptors import PipelineDescriptor
from automator.domain.ports import PipelineRegistry


@dataclass(frozen=True)
class GetPipeline:
    pipelines: PipelineRegistry

    def execute(self, type_id: str) -> PipelineDescriptor:
        return require(self.pipelines.get(type_id), "pipeline", type_id).descriptor
