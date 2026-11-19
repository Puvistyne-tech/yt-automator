from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from autotube.domain.automations import Automation
from autotube.domain.deletion_rules import automations_using
from autotube.domain.model_base import DomainModel, JsonObject
from autotube.domain.pipeline_descriptors import settings_schema_of
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience


class TemplateSummary(PipelineTemplate):
    builtin: bool = Field(description="Packaged with its engine and read-only")
    automations_using: int = Field(ge=0, description="Automations whose pipeline is this template")


class EngineSummary(DomainModel):
    engine_id: str
    name: str
    definition_schema: JsonObject = Field(description="JSON Schema of a template definition")
    definition_ui_schema: JsonObject = Field(description="Form hints for the definition")
    blank: dict[TemplateAudience, JsonObject] = Field(
        description="Starting definition for a new template, per audience"
    )


def template_summary(
    template: PipelineTemplate, automations: Iterable[Automation]
) -> TemplateSummary:
    usage = {
        "builtin": template.is_builtin,
        "automations_using": len(automations_using(template.type_id, automations)),
    }
    return TemplateSummary.model_validate(template.model_dump() | usage)


def engine_summary(engine: PipelineEngine) -> EngineSummary:
    return EngineSummary(
        engine_id=engine.engine_id,
        name=engine.name,
        definition_schema=settings_schema_of(engine.definition_model),
        definition_ui_schema=engine.definition_ui_schema,
        blank={audience: engine.blank(audience) for audience in TemplateAudience},
    )
