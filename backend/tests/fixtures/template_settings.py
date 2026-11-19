from __future__ import annotations

from typing import Any

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_descriptors import default_settings_of
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.merging import deep_merged
from autotube.pipelines.narrated_video.template.settings_model import settings_model_for
from tests.fixtures.kids_data import draft_dict, smart_writer
from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.template_records import template

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL
GENERAL_STORY = "leaf_boat"
GENERAL_CAST = ["mira"]


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


def general_draft() -> dict[str, Any]:
    draft = draft_dict(GENERAL_STORY, refrain="")
    scenes = [
        {**scene, "characters": GENERAL_CAST, "speaker": "narrator"} for scene in draft["scenes"]
    ]
    return {**draft, "scenes": scenes}


def general_story(language: str = "en") -> Story:
    return Story.model_validate(
        {**general_draft(), "language": language, "theme": "a second chance"}
    )


def general_writer() -> FakeWriter:
    return smart_writer(name=GENERAL_STORY, draft=general_draft())
