from __future__ import annotations

from autotube.domain.pipeline_descriptors import KIDS_CONTENT, PipelineDescriptor
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.ui import derived_ui_schema


def template_version(engine_version: str, revision: int) -> str:
    return f"{engine_version}+r{revision}"


def audience_capabilities(capabilities: tuple[str, ...], audience: TemplateAudience) -> list[str]:
    kept = [capability for capability in capabilities if capability != KIDS_CONTENT]
    return [*kept, KIDS_CONTENT] if audience is TemplateAudience.KIDS else kept


def template_descriptor(
    engine: PipelineDescriptor, template: PipelineTemplate, definition: NarratedDefinition
) -> PipelineDescriptor:
    changes = {
        "type_id": template.type_id,
        "name": template.name,
        "description": template.description or engine.description,
        "version": template_version(engine.version, template.revision),
        "ui_schema": derived_ui_schema(engine.ui_schema, definition, template.audience),
        "capabilities": audience_capabilities(engine.capabilities, template.audience),
    }
    return PipelineDescriptor.model_validate({**engine.model_dump(), **changes})
