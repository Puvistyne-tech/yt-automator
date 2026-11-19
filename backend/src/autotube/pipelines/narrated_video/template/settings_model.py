from __future__ import annotations

from copy import deepcopy
from functools import cache, partial
from typing import Any, ClassVar

from pydantic import create_model, model_validator
from pydantic.fields import FieldInfo

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.template.audience import audience_defaults, with_audience
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.kids_floor import audience_floor
from autotube.pipelines.narrated_video.template.mapping import definition_settings
from autotube.pipelines.narrated_video.template.merging import merged_all

SETTINGS_MODEL_NAME = KidsStorySettings.__name__


class AudiencePinnedSettings(KidsStorySettings):
    pinned_audience: ClassVar[TemplateAudience] = TemplateAudience.KIDS

    @model_validator(mode="before")
    @classmethod
    def pin_audience(cls, data: object) -> object:
        pinned = with_audience(data, cls.pinned_audience, cls.section_default)
        return audience_floor(pinned, cls.pinned_audience)

    @classmethod
    def section_default(cls, section: str) -> object:
        return cls.model_fields[section].get_default(call_default_factory=True)


def engine_defaults() -> JsonObject:
    return KidsStorySettings().model_dump(mode="json")


def template_defaults(definition: NarratedDefinition, audience: TemplateAudience) -> JsonObject:
    return merged_all(
        engine_defaults(),
        audience_defaults(audience),
        definition_settings(definition),
        definition.settings,
    )


@cache
def pinned_settings_model(audience: TemplateAudience) -> type[AudiencePinnedSettings]:
    model = create_model(SETTINGS_MODEL_NAME, __base__=AudiencePinnedSettings)
    model.pinned_audience = audience
    return model


def defaulted_field(info: FieldInfo, value: object) -> tuple[Any, FieldInfo]:
    return info.annotation, FieldInfo.merge_field_infos(
        info, default_factory=partial(deepcopy, value)
    )


def settings_model_with(
    pinned: type[AudiencePinnedSettings], defaults: KidsStorySettings
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
    pinned = pinned_settings_model(audience)
    defaults = pinned.model_validate(template_defaults(definition, audience))
    return settings_model_with(pinned, defaults)


def settings_model_for(
    definition: NarratedDefinition, audience: TemplateAudience
) -> type[KidsStorySettings]:
    return settings_model_from_json(definition.model_dump_json(), audience)


def kids_settings_model() -> type[KidsStorySettings]:
    return pinned_settings_model(TemplateAudience.KIDS)
