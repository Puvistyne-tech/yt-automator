from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings

REFUSED = [
    ("item_count", 2),
    ("item_count", 16),
    ("quiz_questions", 0),
    ("quiz_questions", 11),
    ("answer_choices", -1),
    ("answer_choices", 1),
    ("answer_choices", 7),
]
ACCEPTED = [
    ("item_count", 3),
    ("item_count", 15),
    ("quiz_questions", 1),
    ("quiz_questions", 10),
    ("answer_choices", 0),
    ("answer_choices", 2),
    ("answer_choices", 6),
]


def test_the_structure_counts_have_their_defaults() -> None:
    story = KidsStorySettings().story
    assert (story.item_count, story.quiz_questions, story.answer_choices) == (7, 4, 0)


@pytest.mark.parametrize(("field", "value"), REFUSED)
def test_a_count_outside_its_bounds_is_refused(field: str, value: int) -> None:
    with pytest.raises(ValidationError, match=field):
        KidsStorySettings.model_validate({"story": {field: value}})


def test_one_answer_choice_is_refused_with_a_clear_message() -> None:
    with pytest.raises(ValidationError, match="no choices or at least two"):
        KidsStorySettings.model_validate({"story": {"answer_choices": 1}})


@pytest.mark.parametrize(("field", "value"), ACCEPTED)
def test_a_count_on_or_inside_its_bounds_is_kept(field: str, value: int) -> None:
    story = KidsStorySettings.model_validate({"story": {field: value}}).story
    assert getattr(story, field) == value
