from __future__ import annotations

from typing import Any

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_descriptors import default_settings_of
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.merging import deep_merged
from autotube.pipelines.narrated_video.template.settings_model import settings_model_for
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.template_records import template

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL


def model_for(audience: TemplateAudience, **definition: Any) -> type[KidsStorySettings]:
    return settings_model_for(NarratedDefinition.model_validate(definition), audience)


def defaults_for(audience: TemplateAudience = KIDS, **definition: Any) -> dict[str, Any]:
    return default_settings_of(model_for(audience, **definition))


def pipeline_of(audience: TemplateAudience, **definition: Any) -> Pipeline:
    return NarratedVideoEngine().pipeline(template(audience=audience, definition=definition))


def quick_template_settings(
    audience: TemplateAudience = GENERAL, **sections: dict[str, Any]
) -> KidsStorySettings:
    model = model_for(audience)
    extra: dict[str, Any] = {**sections}
    values = deep_merged(deep_merged(default_settings_of(model), QUICK_SECTIONS), extra)
    return model.model_validate(values)
