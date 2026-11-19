from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from tests.fixtures.list_data import (
    list_settings,
    list_story,
    tamil_list,
    with_scene,
)
from tests.fixtures.template_settings import GENERAL, KIDS, pipeline_of

AUDIENCES = [KIDS, GENERAL]


@pytest.mark.parametrize("audience", AUDIENCES)
def test_a_list_model_pins_its_structure_and_the_writer_source(
    audience: TemplateAudience,
) -> None:
    loaded = list_settings(audience, story={"structure": "story", "source": "bundled_only"})
    assert loaded.story.structure is Structure.LIST
    assert loaded.story.source is StorySource.LLM_WITH_FALLBACK
    assert loaded.cast == [] and loaded.story.item_count == 7


@pytest.mark.parametrize("audience", AUDIENCES)
def test_a_written_list_and_its_translation_pass_their_checks(audience: TemplateAudience) -> None:
    settings = list_settings(audience)
    assert story_problems(list_story(), settings) == []
    tamil = tamil_list()
    assert translation_problems(tamil, settings) == []
    assert tamil.scenes[1].heading == "தேனீக்கள் நடனமாடிப் பேசும்"
    assert tamil.scenes[1].number == 1


def test_a_list_needs_its_framing_count_order_and_headings() -> None:
    settings = list_settings(KIDS)
    shuffled = with_scene(with_scene(list_story(), 1, number=2), 2, number=1)
    assert story_problems(shuffled, settings) == ["number the items from 1 up to 7, in that order"]
    repeated = with_scene(list_story(), 2, heading="bees DANCE to talk")
    assert story_problems(repeated, settings) == ["give every item its own heading"]
    blank = with_scene(list_story(), 3, heading=" ")
    assert story_problems(blank, settings) == ["give every item a short heading"]
    framed = with_scene(list_story(), 0, number=8)
    assert story_problems(framed, settings) == [
        "open with an intro scene and end with a closing scene, both without a number",
        "write exactly 7 numbered items, not 8",
        "number the items from 1 up to 8, in that order",
        "give every item a short heading",
    ]


def test_the_list_scene_count_follows_the_item_count() -> None:
    settings = list_settings(GENERAL, story={"item_count": 5})
    found = story_problems(list_story(), settings)
    assert "use exactly 7 scenes, not 9" in found
    assert "write exactly 5 numbered items, not 7" in found
    switched = settings.story.model_copy(update={"enabled_checks": [StoryCheck.WORDS_PER_SCENE]})
    assert story_problems(list_story(), settings.model_copy(update={"story": switched})) == []


def test_a_single_scene_list_has_no_framing() -> None:
    lone = list_story(scenes=[list_story().scenes[0]])
    found = story_problems(lone, list_settings(GENERAL))
    assert any(item.startswith("open with an intro scene") for item in found)


def test_a_list_translation_must_keep_every_scene_label() -> None:
    with pytest.raises(ValueError, match="one scene_labels entry per scene"):
        tamil_list(scene_labels=None)
    with pytest.raises(ValueError, match="one scene_labels entry per scene"):
        tamil_list(scene_labels=[{"heading": "ஒன்று"}])


@pytest.mark.parametrize("audience", AUDIENCES)
def test_the_list_prompts_ask_for_numbered_items(audience: TemplateAudience) -> None:
    settings = list_settings(audience, story={"item_count": 5})
    request = story_request(settings, "facts about honeybees", "en")
    assert "Exactly 7 scenes." in request.prompt
    assert "exactly 5 item scenes, one item per scene, numbered from 1 up to 5" in request.prompt
    assert "short numbered list videos" in (request.system or "")
    assert "$" not in request.prompt and "Cast (" not in request.prompt
    translation = translation_request(settings, list_story(), "en", "ta").prompt
    assert '"scene_labels"' in translation and '"heading": "Bees have five eyes"' in translation


def test_a_list_supplies_its_count_and_items() -> None:
    values = template_values(list_story(), list_settings(GENERAL))
    assert values["count"] == "7"
    assert values["items"].startswith("Bees dance to talk, Bees have five eyes, ")


@pytest.mark.parametrize("audience", AUDIENCES)
def test_the_list_hides_cast_quiz_and_scene_count_settings(audience: TemplateAudience) -> None:
    descriptor = pipeline_of(audience, structure="list").descriptor
    hidden = descriptor.ui_schema["ui:hidden"]
    assert isinstance(hidden, list) and {
        *structure_spec(Structure.LIST).hidden_paths,
        "story.source",
    } <= set(hidden)
    assert "story.item_count" not in hidden
    assert descriptor.default_settings["cast"] == []
