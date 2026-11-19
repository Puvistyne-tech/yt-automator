from __future__ import annotations

import pytest

from autotube.pipelines.narrated_video.settings.story_choices import EndingStyle
from autotube.pipelines.narrated_video.story.checks import story_problems
from autotube.pipelines.narrated_video.story.ending_repair import repaired_ending
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.repair_text import as_sentence, with_lines
from autotube.pipelines.narrated_video.story.repairing import repaired_script
from autotube.pipelines.narrated_video.structures.shape_repairs import (
    repaired_numbers,
    repaired_question_marks,
    repaired_takeaway,
)
from tests.fixtures.explainer_data import TAKEAWAY_ENDING, explainer_settings, explainer_story
from tests.fixtures.kids_data import REFRAIN_EN, quick_settings, story, tamil_draft
from tests.fixtures.list_data import list_settings, list_story, with_scene
from tests.fixtures.quiz_data import quiz_settings, quiz_story
from tests.fixtures.template_settings import GENERAL, KIDS

MORAL = "Sharing makes everyone happier."
REFRAIN_TA = quick_settings().series.refrain.ta


def without_ending(source: Story, *phrases: str) -> Story:
    scenes = list(source.scenes)
    for index in (-2, -1):
        text = scenes[index].narration
        for phrase in phrases:
            text = text.replace(phrase, "").replace(phrase.rstrip(".!"), "")
        scenes[index] = scenes[index].model_copy(update={"narration": text.strip()})
    return source.model_copy(update={"scenes": scenes})


def bare_story() -> Story:
    return without_ending(story(), REFRAIN_EN, '"Sharing makes everyone happier," he said.')


def test_sentences_are_closed_before_lines_are_added() -> None:
    assert as_sentence("Kavin smiled") == "Kavin smiled." and as_sentence("Done!") == "Done!"
    assert with_lines("Kavin smiled", ["Be kind!", "  "]) == "Kavin smiled. Be kind!"


def test_the_ending_gets_the_moral_then_the_refrain() -> None:
    settings = quick_settings()
    assert story_problems(bare_story(), settings) != []
    fixed, notes = repaired_ending(bare_story(), settings)
    assert fixed.scenes[-1].narration.endswith(f"{MORAL} {REFRAIN_EN}")
    assert notes == (
        "added the moral and the refrain to the last scene, as the last 2 scenes must say",
    )
    assert story_problems(fixed, settings) == []
    assert repaired_ending(story(), settings) == (story(), ())


def test_an_empty_moral_is_never_invented() -> None:
    settings = quick_settings()
    fixed, notes = repaired_ending(bare_story().model_copy(update={"moral": " "}), settings)
    assert notes == ("added the refrain to the last scene, as the last 2 scenes must say",)
    assert 'write the moral in "moral"' in story_problems(fixed, settings)


@pytest.mark.parametrize(
    ("style", "added"),
    [(EndingStyle.REFRAIN_ONLY, REFRAIN_EN), (EndingStyle.OPEN, "")],
)
def test_the_ending_repair_follows_the_ending_style(style: EndingStyle, added: str) -> None:
    settings = quick_settings(story={"ending_style": style})
    fixed, notes = repaired_ending(bare_story(), settings)
    assert fixed.scenes[-1].narration.endswith(added or bare_story().scenes[-1].narration)
    assert MORAL not in fixed.scenes[-1].narration
    assert bool(notes) is bool(added)


def test_a_tamil_ending_gets_the_tamil_refrain() -> None:
    tamil = Story.model_validate({**tamil_draft(), "language": "ta"})
    bare = without_ending(tamil, REFRAIN_TA)
    fixed, _ = repaired_ending(bare, quick_settings())
    assert fixed.scenes[-1].narration.endswith(REFRAIN_TA)


def test_the_takeaway_repair_needs_a_takeaway_and_an_ending_that_has_one() -> None:
    settings = explainer_settings(GENERAL, story=TAKEAWAY_ENDING)
    script = explainer_story()
    plain = script.model_copy(update={"scenes": [*script.scenes[:-1], script.scenes[1]]})
    fixed, notes = repaired_takeaway(plain, settings)
    assert notes == ("added the takeaway to the last scene",)
    assert story_problems(fixed, settings) == []
    assert repaired_takeaway(plain.model_copy(update={"moral": ""}), settings)[1] == ()
    assert repaired_takeaway(plain, explainer_settings(GENERAL))[1] == ()


def test_list_items_are_numbered_in_order_when_the_narration_agrees() -> None:
    settings = list_settings(KIDS)
    good = list_story()
    swapped = with_scene(with_scene(good, 1, number=2), 2, number=1)
    fixed, notes = repaired_numbers(swapped, settings, descending=False)
    assert fixed == good and notes == ("numbered the list items in order",)
    spoken = with_scene(swapped, 1, narration="Number 5 is a fact about bees.")
    assert repaired_numbers(spoken, settings, descending=False) == (spoken, ())
    short = good.model_copy(update={"scenes": good.scenes[:-2] + good.scenes[-1:]})
    assert repaired_numbers(short, settings, descending=False) == (short, ())
    assert repaired_numbers(good, settings, descending=False) == (good, ())


def test_a_quiz_question_gets_its_question_mark() -> None:
    settings = quiz_settings(GENERAL)
    good = quiz_story()
    question = good.scenes[1].question
    unmarked = with_scene(good, 1, question=question.rstrip("?"))
    fixed, notes = repaired_question_marks(unmarked, settings)
    assert fixed == good and notes == ("ended every quiz question with a question mark",)
    assert repaired_question_marks(good, settings) == (good, ())


def test_repaired_script_runs_the_structure_repairs_only() -> None:
    swapped = with_scene(with_scene(list_story(), 1, number=2), 2, number=1)
    assert repaired_script(swapped, list_settings(KIDS))[1] == ("numbered the list items in order",)
    assert repaired_script(swapped, quiz_settings(GENERAL))[1] == ()
