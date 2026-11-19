from __future__ import annotations

import builtins
from collections.abc import Sequence

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.ports import TemplateRepository
from autotube.domain.template_rules import servable
from autotube.infrastructure.pipelines.static_registry import indexed


def builtin_pipelines(engines: Sequence[PipelineEngine]) -> dict[str, Pipeline]:
    return indexed(
        [engine.pipeline(template) for engine in engines for template in engine.builtin_templates()]
    )


class TemplatePipelineRegistry:
    def __init__(
        self,
        static: Sequence[Pipeline],
        engines: Sequence[PipelineEngine],
        templates: TemplateRepository,
    ) -> None:
        self.engines = {engine.engine_id: engine for engine in engines}
        self.builtins = builtin_pipelines(engines)
        self.static = {
            type_id: pipeline
            for type_id, pipeline in indexed(static).items()
            if type_id not in self.builtins
        }
        self.reserved = frozenset(self.builtins) | frozenset(self.static)
        self.templates = templates
        self.cache: dict[str, tuple[int, Pipeline]] = {}

    def list(self) -> builtins.list[Pipeline]:
        stored = [
            pipeline
            for template in self.templates.list()
            if (pipeline := self.served(template)) is not None
        ]
        return [*self.static.values(), *self.builtins.values(), *stored]

    def get(self, type_id: str) -> Pipeline | None:
        known = self.builtins.get(type_id) or self.static.get(type_id)
        if known is not None:
            return known
        template = self.templates.find_by_type_id(type_id)
        return self.served(template) if template is not None else None

    def served(self, template: PipelineTemplate) -> Pipeline | None:
        engine = self.engines.get(template.engine)
        if engine is None or not servable(template, self.reserved):
            return None
        hit = self.cache.get(template.type_id)
        if hit is not None and hit[0] == template.revision:
            return hit[1]
        return self.resolved(engine, template)

    def resolved(self, engine: PipelineEngine, template: PipelineTemplate) -> Pipeline | None:
        if engine.problems(template):
            return None
        pipeline = engine.pipeline(template)
        self.cache[template.type_id] = (template.revision, pipeline)
        return pipeline
