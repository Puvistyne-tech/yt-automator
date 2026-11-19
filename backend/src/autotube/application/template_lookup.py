from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require
from autotube.domain.deletion_rules import automations_using
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.ports import (
    AutomationRepository,
    EngineCatalog,
    PipelineRegistry,
    TemplateRepository,
)
from autotube.domain.template_rules import missing_engine_errors
from autotube.domain.template_views import TemplateSummary, template_summary


@dataclass(frozen=True)
class TemplateLookup:
    engines: EngineCatalog
    templates: TemplateRepository
    automations: AutomationRepository
    pipelines: PipelineRegistry

    def builtins(self) -> list[PipelineTemplate]:
        return [
            template for engine in self.engines.list() for template in engine.builtin_templates()
        ]

    def everything(self) -> list[PipelineTemplate]:
        return [*self.builtins(), *self.templates.list()]

    def find(self, template_id: str) -> PipelineTemplate | None:
        builtin = next((t for t in self.builtins() if t.id == template_id), None)
        return builtin or self.templates.get(template_id)

    def require(self, template_id: str) -> PipelineTemplate:
        return require(self.find(template_id), "template", template_id)

    def problems(self, template: PipelineTemplate) -> dict[str, str]:
        engine = self.engines.get(template.engine)
        if engine is None:
            return missing_engine_errors(template.engine)
        return engine.problems(template)

    def taken_type_ids(self) -> set[str]:
        served = {pipeline.descriptor.type_id for pipeline in self.pipelines.list()}
        return served | {template.type_id for template in self.builtins()}

    def users(self, template: PipelineTemplate) -> list[str]:
        return automations_using(template.type_id, self.automations.list())

    def present(self, template: PipelineTemplate) -> TemplateSummary:
        return template_summary(template, self.automations.list())

    def present_all(self, templates: list[PipelineTemplate]) -> list[TemplateSummary]:
        automations = self.automations.list()
        return [template_summary(template, automations) for template in templates]
