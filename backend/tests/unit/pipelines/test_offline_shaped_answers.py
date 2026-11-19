from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotube.infrastructure.providers.llm.offline_text import OfflineText, OfflineTextOptions
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.answer_schema import draft_schema
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompts import story_request
from autotube.pipelines.narrated_video.structures.list_checks import numbers_in_order
from autotube.pipelines.narrated_video.structures.quiz_checks import question_pairs
from tests.fixtures.list_data import list_settings
from tests.fixtures.quiz_data import quiz_settings
from tests.fixtures.template_settings import GENERAL
from tests.unit.infrastructure.providers.fakes import make_context

SHAPED = {
    "list": list_settings(GENERAL),
    "countdown": list_settings(GENERAL, "countdown"),
    "quiz": quiz_settings(GENERAL, story={"answer_choices": 3}),
}


def offline_answer(tmp_path: Path, settings: KidsStorySettings) -> Story:
    writer = OfflineText(OfflineTextOptions(), make_context(tmp_path))
    reply = writer.generate(story_request(settings, "the night sky", "en"))
    return Story.model_validate({**json.loads(reply), "language": "en"})


@pytest.mark.parametrize("settings", list(SHAPED.values()), ids=list(SHAPED))
def test_the_offline_writer_answers_one_scene_per_shape(
    tmp_path: Path, settings: KidsStorySettings
) -> None:
    shapes = draft_schema(settings)["properties"]["scenes"]["prefixItems"]
    assert len(offline_answer(tmp_path, settings).scenes) == len(shapes)


def test_the_offline_countdown_and_quiz_follow_their_shape(tmp_path: Path) -> None:
    assert numbers_in_order(offline_answer(tmp_path, SHAPED["countdown"]), descending=True)
    pairs = question_pairs(offline_answer(tmp_path, SHAPED["quiz"]))
    assert len(pairs) == 4 and all(len(ask.choices) == 3 for ask, _ in pairs)
