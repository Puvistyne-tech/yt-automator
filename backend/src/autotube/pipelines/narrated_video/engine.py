from __future__ import annotations

from pydantic import BaseModel

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline import Pipeline, ProviderResolver
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.pipeline_templates import (
    PipelineTemplate,
    TemplateAudience,
    builtin_template,
)
from autotube.domain.sample_scripts import SampleScript
from autotube.pipelines.narrated_video.plugin import (
    DESCRIPTION,
    NAME,
    TYPE_ID,
    KidsStoryPipeline,
    ui_schema,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.template.builtins import packaged_templates
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.descriptor import template_descriptor
from autotube.pipelines.narrated_video.template.problems import template_problems
from autotube.pipelines.narrated_video.template.revisions import structure_change_problems
from autotube.pipelines.narrated_video.template.sample import template_sample
from autotube.pipelines.narrated_video.template.settings_model import settings_model_for
from autotube.pipelines.narrated_video.template.ui import definition_ui_schema

ENGINE_ID = "narrated_video"
ENGINE_NAME = "Narrated video"


class TemplatePipeline(KidsStoryPipeline):
    def __init__(self, template: PipelineTemplate) -> None:
        super().__init__()
        definition = NarratedDefinition.model_validate(template.definition)
        self.model = settings_model_for(definition, template.audience)
        self.built = template_descriptor(super().descriptor, template, definition)

    @property
    def descriptor(self) -> PipelineDescriptor:
        return self.built

    @property
    def settings_model(self) -> type[KidsStorySettings]:
        return self.model


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
        return definition_ui_schema()

    def blank(self, audience: TemplateAudience) -> JsonObject:  # noqa: ARG002
        return NarratedDefinition().model_dump(mode="json", exclude_defaults=True)

    def problems(self, template: PipelineTemplate) -> dict[str, str]:
        errors = template_problems(template, ui_schema())
        if template.engine != ENGINE_ID:
            errors["engine"] = f"template belongs to engine {template.engine!r}, not {ENGINE_ID!r}"
        return errors

    def revision_problems(
        self, current: PipelineTemplate, proposed: PipelineTemplate
    ) -> dict[str, str]:
        return structure_change_problems(current, proposed)

    def pipeline(self, template: PipelineTemplate) -> Pipeline:
        if template.is_builtin and template.type_id == TYPE_ID:
            return self.kids_story
        return TemplatePipeline(template)

    def sample_script(
        self, template: PipelineTemplate, language: str, topic: str, providers: ProviderResolver
    ) -> SampleScript:
        return template_sample(template, language, topic, providers)

    def builtin_templates(self) -> list[PipelineTemplate]:
        kids = TemplateAudience.KIDS
        kids_story = builtin_template(ENGINE_ID, TYPE_ID, NAME, DESCRIPTION, kids, self.blank(kids))
        return [kids_story, *packaged_templates(ENGINE_ID)]
