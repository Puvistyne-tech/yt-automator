from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from tests.fixtures.list_data import with_scene
from tests.fixtures.quiz_data import quiz_settings, quiz_story, tamil_quiz
from tests.fixtures.template_settings import GENERAL, KIDS

AUDIENCES = [KIDS, GENERAL]
CHOICES: dict[str, Any] = {"story": {"answer_choices": 3}}


@pytest.mark.parametrize("audience", AUDIENCES)
@pytest.mark.parametrize("choices", [False, True])
def test_a_written_quiz_and_its_translation_pass_their_checks(
    audience: TemplateAudience, choices: bool
) -> None:
    settings = quiz_settings(audience, **(CHOICES if choices else {}))
    assert settings.story.structure is Structure.QUIZ
    assert story_problems(quiz_story(choices), settings) == []
    tamil = tamil_quiz(choices)
    assert translation_problems(tamil, settings) == []
    assert tamil.scenes[2].answer == "புதன்"


@pytest.mark.parametrize(
    ("index", "changes", "problem"),
    [
        (
            1,
            {"question": "Which planet is closest to the sun"},
            "end question 1 with a question mark",
        ),
        (2, {"answer": ""}, "follow question 1 with a reveal scene that gives its answer"),
        (4, {"answer": "Venus"}, "say the answer to question 2, word for word, in its reveal"),
        (
            1,
            {"choices": ["Mercury", "Venus"]},
            "ask question 1 as an open question, with no choices",
        ),
    ],
)
def test_a_quiz_checks_every_question_and_reveal(
    index: int, changes: dict[str, Any], problem: str
) -> None:
    broken = with_scene(quiz_story(), index, **changes)
    assert story_problems(broken, quiz_settings(GENERAL)) == [problem]


def test_a_quiz_with_choices_needs_them_and_the_answer_among_them() -> None:
    settings = quiz_settings(KIDS, **CHOICES)
    assert story_problems(quiz_story(), settings) == [
        f"give question {number} exactly 3 choices" for number in range(1, 5)
    ]
    two = with_scene(quiz_story(choices=True), 1, choices=["Mercury", "Venus"])
    assert story_problems(two, settings) == ["give question 1 exactly 3 choices"]
    moved = with_scene(quiz_story(choices=True), 3, choices=["two moons", "three", "four"])
    assert story_problems(moved, settings) == ["make the answer to question 2 one of its choices"]


def test_a_quiz_needs_framing_and_the_question_count() -> None:
    scenes = quiz_story().scenes
    short = quiz_story(scenes=[*scenes[1:7], scenes[-1]])
    found = story_problems(short, quiz_settings(GENERAL))
    assert found[0] == "use exactly 10 scenes, not 7"
    assert found[-2:] == [
        "open with an intro scene and end with a closing scene, with no question or answer",
        "ask exactly 4 questions, not 3",
    ]
    unanswered = quiz_story(scenes=[*scenes[:-1], scenes[1]])
    found = story_problems(unanswered, quiz_settings(GENERAL))
    assert "follow question 5 with a reveal scene that gives its answer" in found


@pytest.mark.parametrize("choices", [0, 3])
def test_the_quiz_prompts_ask_for_questions_and_reveals(choices: int) -> None:
    settings = quiz_settings(GENERAL, story={"quiz_questions": 3, "answer_choices": choices})
    request = story_request(settings, "the night sky", "en")
    assert "Exactly 8 scenes." in request.prompt
    assert "exactly 3 pairs of scenes" in request.prompt
    expected = "lists exactly 3 short possible answers" if choices else "the questions are open"
    assert expected in request.prompt and "$" not in request.prompt
    assert "short quiz videos" in (request.system or "")
    translation = translation_request(settings, quiz_story(), "en", "ta").prompt
    assert '"scene_labels"' in translation and "question mark" in translation


def test_a_quiz_supplies_its_question_count() -> None:
    assert template_values(quiz_story(), quiz_settings(GENERAL))["question_count"] == "4"
