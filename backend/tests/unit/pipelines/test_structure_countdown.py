from __future__ import annotations

from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from tests.fixtures.list_data import list_settings, list_story, tamil_list
from tests.fixtures.template_settings import KIDS

DESCENDING = "number the items from 7 down to 1, so the last item is number 1"


def test_a_countdown_must_end_on_number_one() -> None:
    settings = list_settings(KIDS, "countdown")
    assert story_problems(list_story(), settings) == [DESCENDING]
    assert translation_problems(tamil_list(), settings) == [DESCENDING]
    assert story_problems(list_story(countdown=True), list_settings(KIDS)) == [
        "number the items from 1 up to 7, in that order"
    ]
