from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.model import Story, StoryText, text_of, with_text
from tests.fixtures.kids_data import english_text, story
from tests.fixtures.list_data import list_settings, list_story, with_scene
from tests.fixtures.quiz_data import quiz_settings, quiz_story
from tests.fixtures.template_settings import GENERAL, KIDS

NEW_SCENE_KEYS = ("number", "heading", "question", "choices", "answer")


def stored_payload() -> dict[str, Any]:
    payload = story().model_dump(mode="json", exclude={"moral"})
    payload["scenes"] = [
        {key: value for key, value in scene.items() if key not in NEW_SCENE_KEYS}
        for scene in payload["scenes"]
    ]
    return payload


def test_a_stored_script_without_a_moral_or_scene_labels_still_validates() -> None:
    payload = stored_payload()
    assert "moral" not in payload and not set(NEW_SCENE_KEYS) & set(payload["scenes"][0])
    loaded = Story.model_validate(payload)
    assert loaded.moral == "" and loaded.scenes[0].number is None
    assert loaded.scenes[0].texts == ["", "", ""]
    text = StoryText.model_validate({"title": "A title", "narrations": ["One line."]})
    assert text.moral == "" and text.scene_labels is None


@pytest.mark.parametrize(
    ("sample", "settings"),
    [
        (list_story(moral=""), list_settings(KIDS)),
        (list_story(countdown=True, moral=""), list_settings(GENERAL, "countdown")),
        (quiz_story(moral=""), quiz_settings(GENERAL)),
    ],
    ids=["list", "countdown", "quiz"],
)
def test_lists_countdowns_and_quizzes_need_no_moral(
    sample: Story, settings: KidsStorySettings
) -> None:
    assert story_problems(sample, settings) == []
    assert translation_problems(sample, settings) == []


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
