from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require
from autotube.domain.automations import Automation
from autotube.domain.pipeline_engine import PipelineEngine, builtin_templates_of
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.ports import (
    AutomationRepository,
    EngineCatalog,
    PipelineRegistry,
    RunRepository,
    TemplateRepository,
)
from autotube.domain.runs import Run, RunQuery
from autotube.domain.template_rules import found_template, missing_engine_errors, taken_type_ids
from autotube.domain.template_views import TemplateSummary, template_summary
from autotube.shared.errors import ValidationFailed, raise_if_invalid


@dataclass(frozen=True)
class TemplateLookup:
    engines: EngineCatalog
    templates: TemplateRepository
    automations: AutomationRepository
    runs: RunRepository
    pipelines: PipelineRegistry

    def builtins(self) -> list[PipelineTemplate]:
        return builtin_templates_of(self.engines.list())

    def everything(self) -> list[PipelineTemplate]:
        return [*self.builtins(), *self.templates.list()]

    def find(self, template_id: str) -> PipelineTemplate | None:
        return found_template(template_id, self.builtins(), self.templates.get(template_id))

    def require(self, template_id: str) -> PipelineTemplate:
        return require(self.find(template_id), "template", template_id)

    def problems(self, template: PipelineTemplate) -> dict[str, str]:
        engine = self.engines.get(template.engine)
        if engine is None:
            return missing_engine_errors(template.engine)
        return engine.problems(template)

    def engine_by_id(self, engine_id: str) -> PipelineEngine:
        engine = self.engines.get(engine_id)
        if engine is None:
            raise ValidationFailed(missing_engine_errors(engine_id))
        return engine

    def engine_for(self, template: PipelineTemplate) -> PipelineEngine:
        return self.engine_by_id(template.engine)

    def valid_engine(self, template: PipelineTemplate) -> PipelineEngine:
        engine = self.engine_for(template)
        raise_if_invalid(engine.problems(template))
        return engine

    def revision_problems(
        self, current: PipelineTemplate, proposed: PipelineTemplate
    ) -> dict[str, str]:
        engine = self.engines.get(proposed.engine)
        fixed = {} if engine is None else engine.revision_problems(current, proposed)
        return self.problems(proposed) | fixed

    def taken_type_ids(self) -> set[str]:
        served = (pipeline.descriptor.type_id for pipeline in self.pipelines.list())
        return taken_type_ids(served, self.builtins())

    def all_automations(self) -> list[Automation]:
        return self.automations.list()

    def all_runs(self) -> list[Run]:
        return self.runs.list(RunQuery())

    def present(self, template: PipelineTemplate) -> TemplateSummary:
        return template_summary(template, self.all_automations())

    def present_all(self, templates: list[PipelineTemplate]) -> list[TemplateSummary]:
        automations = self.all_automations()
        return [template_summary(template, automations) for template in templates]
