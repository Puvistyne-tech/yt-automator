from __future__ import annotations

import pytest

from autotube.pipelines.narrated_video.story.prompt_parts import scene_words_rule


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
