from __future__ import annotations

import pytest

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.model import Story, StoryText, text_of, with_text
from tests.fixtures.explainer_data import explainer_settings, explainer_story
from tests.fixtures.kids_data import english_text, story
from tests.fixtures.list_data import list_settings, list_story, with_scene
from tests.fixtures.template_settings import GENERAL, KIDS

NO_MORAL = 'write the moral in "moral"'


def test_a_script_without_a_moral_or_scene_labels_still_validates() -> None:
    loaded = Story.model_validate({**story().model_dump(), "moral": ""})
    assert loaded.moral == "" and loaded.scenes[0].number is None
    assert loaded.scenes[0].texts == ["", "", ""]


@pytest.mark.parametrize(
    ("sample", "settings"),
    [(story(), KidsStorySettings()), (explainer_story(), explainer_settings(GENERAL))],
)
def test_story_and_explainer_still_require_a_moral(
    sample: Story, settings: KidsStorySettings
) -> None:
    moralless = sample.model_copy(update={"moral": " "})
    assert NO_MORAL in story_problems(moralless, settings)
    assert NO_MORAL in translation_problems(moralless, settings)


def test_a_list_needs_no_moral() -> None:
    assert story_problems(list_story(moral=""), list_settings(KIDS)) == []


def test_a_script_without_labels_translates_without_them() -> None:
    assert text_of(story()).scene_labels is None
    text = StoryText.model_validate({**english_text(), "scene_labels": [{"heading": "x"}]})
    translated = with_text(story(), text, "ta")
    assert all(scene.heading == "" for scene in translated.scenes)


def test_scene_labels_travel_with_the_text() -> None:
    labelled = with_scene(list_story(), 0, question="Ready?", choices=["yes", "no"], answer="yes")
    labels = text_of(labelled).scene_labels
    assert labels is not None and labels[0].texts == ["", "Ready?", "yes", "no", "yes"]
    assert labels[1].heading == "Bees dance to talk"
