from __future__ import annotations

from copy import deepcopy
from functools import cache, partial
from typing import Any, ClassVar, Self

from pydantic import create_model, model_validator
from pydantic.fields import FieldInfo

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.length import length_problem
from autotube.pipelines.narrated_video.structures.registry import structure_defaults
from autotube.pipelines.narrated_video.template.audience import audience_defaults, with_pins
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.kids_floor import audience_floor
from autotube.pipelines.narrated_video.template.mapping import definition_settings
from autotube.pipelines.narrated_video.template.merging import merged_all
from autotube.pipelines.narrated_video.template.structure_pins import template_pins

SETTINGS_MODEL_NAME = KidsStorySettings.__name__


class PinnedSettings(KidsStorySettings):
    pinned_audience: ClassVar[TemplateAudience] = TemplateAudience.KIDS
    pinned_structure: ClassVar[Structure] = Structure.STORY

    @model_validator(mode="before")
    @classmethod
    def pin_template(cls, data: object) -> object:
        pins = template_pins(cls.pinned_audience, cls.pinned_structure)
        pinned = with_pins(data, pins, cls.section_default)
        return audience_floor(pinned, cls.pinned_audience)

    @model_validator(mode="after")
    def fit_length(self) -> Self:
        problem = length_problem(self)
        if problem:
            raise ValueError(problem)
        return self

    @classmethod
    def section_default(cls, section: str) -> object:
        return cls.model_fields[section].get_default(call_default_factory=True)


def engine_defaults() -> JsonObject:
    return KidsStorySettings().model_dump(mode="json")


def template_defaults(definition: NarratedDefinition, audience: TemplateAudience) -> JsonObject:
    return merged_all(
        engine_defaults(),
        audience_defaults(audience),
        *structure_defaults(definition.structure),
        definition_settings(definition),
        definition.settings,
    )


@cache
def pinned_settings_model(
    audience: TemplateAudience, structure: Structure = Structure.STORY
) -> type[PinnedSettings]:
    model = create_model(SETTINGS_MODEL_NAME, __base__=PinnedSettings)
    model.pinned_audience = audience
    model.pinned_structure = structure
    return model


def defaulted_field(info: FieldInfo, value: object) -> tuple[Any, FieldInfo]:
    return info.annotation, FieldInfo.merge_field_infos(
        info, default_factory=partial(deepcopy, value)
    )


def settings_model_with(
    pinned: type[PinnedSettings], defaults: KidsStorySettings
) -> type[KidsStorySettings]:
    fields: dict[str, Any] = {
        name: defaulted_field(info, getattr(defaults, name))
        for name, info in KidsStorySettings.model_fields.items()
    }
    return create_model(SETTINGS_MODEL_NAME, __base__=pinned, **fields)


@cache
def settings_model_from_json(
    definition_json: str, audience: TemplateAudience
) -> type[KidsStorySettings]:
    definition = NarratedDefinition.model_validate_json(definition_json)
    pinned = pinned_settings_model(audience, definition.structure)
    defaults = pinned.model_validate(template_defaults(definition, audience))
    return settings_model_with(pinned, defaults)


def settings_model_for(
    definition: NarratedDefinition, audience: TemplateAudience
) -> type[KidsStorySettings]:
    return settings_model_from_json(definition.model_dump_json(), audience)


def kids_settings_model() -> type[KidsStorySettings]:
    return pinned_settings_model(TemplateAudience.KIDS)
