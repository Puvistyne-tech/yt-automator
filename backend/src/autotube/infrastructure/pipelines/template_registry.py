from __future__ import annotations

import builtins
from collections.abc import Sequence

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_engine import builtin_templates_of
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.ports import EngineCatalog, TemplateRepository
from autotube.domain.template_rules import servable
from autotube.infrastructure.pipelines.pipeline_index import indexed


def builtin_pipelines(engines: EngineCatalog) -> dict[str, Pipeline]:
    return indexed(
        [
            engine.pipeline(template)
            for template in builtin_templates_of(engines.list())
            if (engine := engines.get(template.engine)) is not None
            and not engine.problems(template)
        ]
    )


class TemplatePipelineRegistry:
    def __init__(
        self,
        static: Sequence[Pipeline],
        engines: EngineCatalog,
        templates: TemplateRepository,
    ) -> None:
        self.engines = engines
        self.builtins = builtin_pipelines(engines)
        self.static = {
            type_id: pipeline
            for type_id, pipeline in indexed(static).items()
            if type_id not in self.builtins
        }
        self.reserved = frozenset(self.builtins) | frozenset(self.static)
        self.templates = templates
        self.cache: dict[str, tuple[PipelineTemplate, Pipeline]] = {}

    def list(self) -> builtins.list[Pipeline]:
        return [*self.static.values(), *self.builtins.values(), *self.stored()]

    def get(self, type_id: str) -> Pipeline | None:
        known = self.builtins.get(type_id) or self.static.get(type_id)
        if known is not None:
            return known
        template = self.templates.find_by_type_id(type_id)
        if template is None:
            self.cache.pop(type_id, None)
            return None
        return self.served(template)

    def stored(self) -> builtins.list[Pipeline]:
        templates = self.templates.list()
        present = {template.type_id for template in templates}
        for type_id in set(self.cache) - present:
            self.cache.pop(type_id, None)
        return [pipeline for template in templates if (pipeline := self.served(template))]

    def served(self, template: PipelineTemplate) -> Pipeline | None:
        hit = self.cache.get(template.type_id)
        if hit is not None and hit[0] == template:
            return hit[1]
        self.cache.pop(template.type_id, None)
        pipeline = self.built(template)
        if pipeline is not None:
            self.cache[template.type_id] = (template, pipeline)
        return pipeline

    def built(self, template: PipelineTemplate) -> Pipeline | None:
        engine = self.engines.get(template.engine)
        if engine is None or not servable(template, self.reserved) or engine.problems(template):
            return None
        return engine.pipeline(template)
