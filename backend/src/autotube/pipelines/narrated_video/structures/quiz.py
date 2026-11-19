from __future__ import annotations

from autotube.pipelines.narrated_video.languages import language_name
from autotube.pipelines.narrated_video.resources import render_prompt
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.gates import CheckedGate
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompt_parts import following_bullets
from autotube.pipelines.narrated_video.structures.castless import LABELS_RULE, NO_STORY_LINES
from autotube.pipelines.narrated_video.structures.paths import (
    CAST_PATHS,
    QUIZ_COUNT_PATHS,
    SCENE_COUNT_PATHS,
)
from autotube.pipelines.narrated_video.structures.quiz_checks import (
    question_pairs,
    quiz_problems,
    quiz_scene_range,
)
from autotube.pipelines.narrated_video.structures.shape_score import structure_item
from autotube.pipelines.narrated_video.structures.spec import StructureSpec, unseeded

WORDING = {"format": "quiz", "pieces": "quiz scripts", "piece": "quiz script"}
OPEN_QUESTIONS = '"choices" is always an empty list: the questions are open.'
TRANSLATION_RULES = (
    LABELS_RULE,
    "Every translated question still ends with a question mark.",
    "Each translated answer appears word for word inside its reveal narration, and stays one of "
    "the translated choices when there are choices.",
)
HIDDEN_PATHS = (*CAST_PATHS, *SCENE_COUNT_PATHS)
QUIZ_GATES: tuple[CheckedGate, ...] = ((StoryCheck.STRUCTURE, quiz_problems),)


def choices_rule(count: int, language: str) -> str:
    if not count:
        return OPEN_QUESTIONS
    return (
        f'"choices" lists exactly {count} short possible answers in {language}, one of them the '
        "answer written exactly as in the reveal, and the narration reads them out."
    )


def quiz_values(
    settings: KidsStorySettings,
    language: str,
    seed: str,  # noqa: ARG001
) -> dict[str, str]:
    name = language_name(language)
    rules = render_prompt(
        "quiz.txt",
        count=settings.story.quiz_questions,
        language=name,
        choices_rule=choices_rule(settings.story.answer_choices, name),
    )
    return {**NO_STORY_LINES, "structure_rules": rules}


def quiz_rules(settings: KidsStorySettings, language: str) -> str:  # noqa: ARG001
    return following_bullets(TRANSLATION_RULES)


def question_count_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:  # noqa: ARG001
    return {"question_count": str(len(question_pairs(story)))}


QUIZ_SPEC = StructureSpec(
    id=Structure.QUIZ,
    title="Quiz",
    wording=WORDING,
    prompt_values=quiz_values,
    translation_rules=quiz_rules,
    extra_gates=unseeded(QUIZ_GATES),
    translation_gates=QUIZ_GATES,
    score_rules=(structure_item("Quiz questions and reveals", quiz_problems),),
    placeholders=("question_count",),
    placeholder_values=question_count_values,
    hidden_paths=HIDDEN_PATHS,
    shown_paths=QUIZ_COUNT_PATHS,
    defaults_file="quiz_defaults.json",
    scene_range=quiz_scene_range,
)
