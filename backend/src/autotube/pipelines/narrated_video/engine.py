from __future__ import annotations

from pydantic import BaseModel

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.pipeline_templates import (
    PipelineTemplate,
    TemplateAudience,
    builtin_template,
)
from autotube.domain.validation import validated_settings
from autotube.pipelines.narrated_video.plugin import DESCRIPTION, NAME, TYPE_ID, KidsStoryPipeline
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition

ENGINE_ID = "narrated_video"
ENGINE_NAME = "Narrated video"


class TemplatePipeline(KidsStoryPipeline):
    def __init__(self, template: PipelineTemplate) -> None:
        super().__init__()
        self.template = template

    @property
    def descriptor(self) -> PipelineDescriptor:
        named = {"type_id": self.template.type_id, "name": self.template.name}
        return super().descriptor.model_copy(update=named)


class NarratedVideoEngine:
    def __init__(self) -> None:
        self.kids_story = KidsStoryPipeline()

    @property
    def engine_id(self) -> str:
        return ENGINE_ID

    @property
    def name(self) -> str:
        return ENGINE_NAME

    @property
    def definition_model(self) -> type[BaseModel]:
        return NarratedDefinition

    @property
    def definition_ui_schema(self) -> JsonObject:
        return {}

    def blank(self, audience: TemplateAudience) -> JsonObject:  # noqa: ARG002
        return NarratedDefinition().model_dump(mode="json")

    def problems(self, template: PipelineTemplate) -> dict[str, str]:
        _, errors = validated_settings(NarratedDefinition, template.definition, "definition")
        if template.engine != ENGINE_ID:
            errors["engine"] = f"template belongs to engine {template.engine!r}, not {ENGINE_ID!r}"
        return errors

    def pipeline(self, template: PipelineTemplate) -> Pipeline:
        if template.is_builtin and template.type_id == TYPE_ID:
            return self.kids_story
        return TemplatePipeline(template)

    def builtin_templates(self) -> list[PipelineTemplate]:
        kids = TemplateAudience.KIDS
        return [builtin_template(ENGINE_ID, TYPE_ID, NAME, DESCRIPTION, kids, self.blank(kids))]
