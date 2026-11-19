from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.domain.pipeline_descriptors import KIDS_CONTENT
from autotube.domain.pipeline_templates import (
    USER_TYPE_PREFIX,
    PipelineTemplate,
    TemplateAudience,
    TemplateOrigin,
    TemplateStatus,
)
from autotube.pipelines.narrated_video.engine import ENGINE_ID, NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.series import BANNED_WORDS, BRAND_NAMES
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in_any
from autotube.pipelines.narrated_video.styles.library import style_ids
from autotube.pipelines.narrated_video.template.builtins import PackagedTemplate
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.length_problems import length_problems
from autotube.pipelines.narrated_video.template.placeholder_problems import placeholder_problems
from autotube.pipelines.narrated_video.template.term_screen import (
    child_term_problems,
    style_texts,
)
from tests.fixtures.builtin_catalog import BUILTIN_IDS, PACKAGED_FORMATS
from tests.fixtures.template_records import template

LANGUAGES = ("en", "ta")
MINIMUM_TOPICS = 12
ENGINE = NarratedVideoEngine()
PACKAGED = [item for item in ENGINE.builtin_templates() if item.id in PACKAGED_FORMATS]
GENERAL = [item for item in PACKAGED if item.audience is TemplateAudience.GENERAL]
KIDS = [item for item in PACKAGED if item.audience is TemplateAudience.KIDS]


def definition_of(template: PipelineTemplate) -> NarratedDefinition:
    return NarratedDefinition.model_validate(template.definition)


def settings_of(template: PipelineTemplate) -> KidsStorySettings:
    settings = ENGINE.pipeline(template).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def test_the_builtins_are_listed_in_a_stable_order_with_kids_story_first() -> None:
    assert [item.id for item in ENGINE.builtin_templates()] == BUILTIN_IDS
    assert [item.id for item in NarratedVideoEngine().builtin_templates()] == BUILTIN_IDS


@pytest.mark.parametrize("template", ENGINE.builtin_templates(), ids=lambda item: item.id)
def test_every_builtin_is_a_ready_read_only_template_of_the_engine(
    template: PipelineTemplate,
) -> None:
    assert template.type_id == template.id
    assert not template.type_id.startswith(USER_TYPE_PREFIX)
    assert (template.engine, template.origin, template.status, template.revision) == (
        ENGINE_ID,
        TemplateOrigin.BUILTIN,
        TemplateStatus.READY,
        1,
    )
    assert ENGINE.problems(template) == {}


@pytest.mark.parametrize("template", PACKAGED, ids=lambda item: item.id)
def test_every_packaged_builtin_has_a_complete_definition(template: PipelineTemplate) -> None:
    definition = definition_of(template)
    assert (definition.structure.value, template.audience) == PACKAGED_FORMATS[template.id]
    assert template.name and template.description.endswith(".")
    assert definition.brief and definition.tone and definition.music_mood
    assert len(definition.topics) >= MINIMUM_TOPICS
    assert len(set(definition.topics)) == len(definition.topics)
    assert definition.visual_style in style_ids()
    localized = (
        definition.title_template,
        definition.short_title_template,
        definition.description_template,
        definition.tags,
        definition.hashtags,
    )
    assert all(getattr(value, code) for value in localized for code in LANGUAGES)
    assert placeholder_problems(definition) == {}
    assert length_problems(definition, template.audience) == {}


@pytest.mark.parametrize("template", GENERAL, ids=lambda item: item.id)
def test_general_builtins_pass_the_child_term_screen(template: PipelineTemplate) -> None:
    definition = definition_of(template)
    assert child_term_problems(template, definition) == {}
    screened = [template.name, template.description, *style_texts(definition.visual_style)]
    assert child_terms_in_any(screened) == []


@pytest.mark.parametrize("template", PACKAGED, ids=lambda item: item.id)
def test_every_packaged_builtin_is_served_with_its_audience(template: PipelineTemplate) -> None:
    pipeline = ENGINE.pipeline(template)
    descriptor = pipeline.descriptor
    assert (descriptor.type_id, descriptor.name) == (template.type_id, template.name)
    kids = template.audience is TemplateAudience.KIDS
    assert (KIDS_CONTENT in descriptor.capabilities) is kids
    assert settings_of(template).safety.for_kids is kids


@pytest.mark.parametrize("template", KIDS, ids=lambda item: item.id)
def test_the_kids_builtin_carries_the_kids_floor(template: PipelineTemplate) -> None:
    settings = settings_of(template)
    assert set(BANNED_WORDS) <= set(settings.safety.banned_words)
    assert set(BRAND_NAMES) <= set(settings.safety.brand_names)
    assert StoryCheck.READING_LEVEL in settings.story.enabled_checks


def test_a_packaged_builtin_may_not_take_a_user_type_id() -> None:
    entry = {"name": "N", "description": "D.", "audience": "general", "definition": {}}
    with pytest.raises(ValidationError, match="user templates"):
        PackagedTemplate.model_validate({**entry, "id": f"{USER_TYPE_PREFIX}facts"})
    assert PackagedTemplate.model_validate({**entry, "id": "facts"}).template(ENGINE_ID).id == (
        "facts"
    )


CHILD_WORDED_STYLES = [style for style in style_ids() if child_terms_in_any(style_texts(style))]


@pytest.mark.parametrize("style", CHILD_WORDED_STYLES)
def test_a_child_worded_style_is_refused_on_a_general_template(style: str) -> None:
    general = template(definition={"visual_style": style})
    assert "definition.visual_style" in ENGINE.problems(general)
    kids = template(audience=TemplateAudience.KIDS, definition={"visual_style": style})
    assert ENGINE.problems(kids) == {}
