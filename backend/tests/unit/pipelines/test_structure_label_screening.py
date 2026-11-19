from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from tests.fixtures.list_data import list_settings, list_story, with_scene
from tests.fixtures.quiz_data import quiz_settings, quiz_story
from tests.fixtures.template_settings import GENERAL, KIDS

SCREENED: list[tuple[dict[str, Any], str]] = [
    ({"heading": "Fun for kids"}, "never address children"),
    ({"question": "Is the monster asleep?"}, "remove these words: monster"),
    ({"choices": ["a Lego tower", "a hive"]}, "remove these brand names: Lego"),
    ({"answer": "the little ones"}, "never address children"),
]


@pytest.mark.parametrize(("labels", "found"), SCREENED)
def test_every_scene_label_is_screened_like_the_narration(
    labels: dict[str, Any], found: str
) -> None:
    labelled = with_scene(list_story(), 0, **labels)
    settings = list_settings(GENERAL, safety={"banned_words": ["monster"]})
    assert any(found in item for item in story_problems(labelled, settings))
    assert any(found in item for item in translation_problems(labelled, settings))


@pytest.mark.parametrize(("labels", "found"), SCREENED[1:])
def test_quiz_scene_labels_are_screened(labels: dict[str, Any], found: str) -> None:
    labelled = with_scene(quiz_story(choices=True), 1, **labels)
    settings = quiz_settings(GENERAL, safety={"banned_words": ["monster"]})
    assert any(found in item for item in story_problems(labelled, settings))


def test_kids_scripts_may_address_children_in_their_labels() -> None:
    labelled = with_scene(list_story(), 0, heading="Fun for kids")
    assert story_problems(labelled, list_settings(KIDS)) == []


@pytest.mark.parametrize("label", ["heading", "question", "answer"])
def test_kids_labels_count_towards_the_reading_level(label: str) -> None:
    wordy = with_scene(list_story(), 0, **{label: " ".join(["wonderfully"] * 60)})
    assert "use fewer long words" in story_problems(wordy, list_settings(KIDS))
    assert story_problems(wordy, list_settings(GENERAL)) == []
    long_sentence = with_scene(list_story(), 0, **{label: " ".join(["bee"] * 120)})
    assert "use shorter sentences" in " ".join(story_problems(long_sentence, list_settings(KIDS)))
