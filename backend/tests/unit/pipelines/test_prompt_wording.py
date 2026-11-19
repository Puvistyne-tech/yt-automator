from __future__ import annotations

import pytest

from autotube.pipelines.narrated_video.settings.story_choices import EndingStyle
from autotube.pipelines.narrated_video.story.prompt_parts import (
    ending_requirement,
    scene_words_rule,
)


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        ((25, 25), "Write about 25 words in each scene's narration"),
        ((37, 38), "Write about 38 words in each scene's narration, from 37 to 38"),
        ((30, 45), "Each scene's narration has between 30 and 45 words"),
    ],
)
def test_the_scene_word_rule_says_about_n_when_the_range_is_narrow(
    span: tuple[int, int], expected: str
) -> None:
    assert scene_words_rule(span) == expected


@pytest.mark.parametrize(
    ("style", "expected"),
    [
        (EndingStyle.MORAL_AND_REFRAIN, "The last scene says the moral word for word."),
        (EndingStyle.REFRAIN_ONLY, "Do not say the moral aloud; let the story show it."),
    ],
)
@pytest.mark.parametrize("refrain", ["", "   "])
def test_a_blank_refrain_is_never_asked_for(
    style: EndingStyle, expected: str, refrain: str
) -> None:
    assert ending_requirement(style, refrain, for_kids=False) == expected


def test_a_refrain_is_quoted_when_there_is_one() -> None:
    rule = ending_requirement(EndingStyle.MORAL_AND_REFRAIN, "Sleep well.", for_kids=True)
    assert rule.endswith('ends with this exact refrain: "Sleep well."')
