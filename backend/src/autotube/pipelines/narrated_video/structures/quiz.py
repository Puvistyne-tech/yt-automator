from __future__ import annotations

from autotube.pipelines.narrated_video.languages import language_name
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.castless import LABELS_RULE, castless_values
from autotube.pipelines.narrated_video.structures.paths import COUNTED_PATHS, QUIZ_COUNT_PATHS
from autotube.pipelines.narrated_video.structures.quiz_checks import (
    question_pairs,
    quiz_problems,
    quiz_scenes,
)
from autotube.pipelines.narrated_video.structures.scene_shapes import quiz_shapes
from autotube.pipelines.narrated_video.structures.shape_spec import Shape, shape_spec

WORDING = {"format": "quiz", "pieces": "quiz scripts", "piece": "quiz script"}
OPEN_QUESTIONS = '"choices" is always an empty list: the questions are open.'
TRANSLATION_RULES = (
    LABELS_RULE,
    "Every translated question still ends with a question mark.",
    "Each translated answer appears word for word inside its reveal narration, and stays one of "
    "the translated choices when there are choices.",
)


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
    return castless_values(
        "quiz.txt",
        count=settings.story.quiz_questions,
        language=name,
        choices_rule=choices_rule(settings.story.answer_choices, name),
    )


def question_count_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:  # noqa: ARG001
    return {"question_count": str(len(question_pairs(story)))}


QUIZ_SPEC = shape_spec(
    Shape(
        structure=Structure.QUIZ,
        title="Quiz",
        wording=WORDING,
        problems=quiz_problems,
        score_title="Quiz questions and reveals",
        prompt_values=quiz_values,
        translation_rules=TRANSLATION_RULES,
        placeholders=("question_count",),
        placeholder_values=question_count_values,
        hidden_paths=COUNTED_PATHS,
        shown_paths=QUIZ_COUNT_PATHS,
        fixed_scenes=quiz_scenes,
        scene_shapes=quiz_shapes,
    )
)
