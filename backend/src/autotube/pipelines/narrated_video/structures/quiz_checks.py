from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryScene
from autotube.pipelines.narrated_video.story.words import contains_phrase
from autotube.pipelines.narrated_video.structures.explainer_checks import QUESTION_MARKS
from autotube.pipelines.narrated_video.structures.list_checks import FRAMING_SCENES

SCENES_PER_QUESTION = 2


def quiz_scene_range(settings: KidsStorySettings) -> tuple[int, int]:
    total = settings.story.quiz_questions * SCENES_PER_QUESTION + FRAMING_SCENES
    return total, total


def asks(scene: StoryScene) -> bool:
    return bool(scene.question.strip())


def reveals(scene: StoryScene) -> bool:
    return bool(scene.answer.strip())


def question_pairs(story: Story) -> list[tuple[StoryScene, StoryScene | None]]:
    scenes = story.scenes
    return [
        (scene, scenes[index + 1] if index + 1 < len(scenes) else None)
        for index, scene in enumerate(scenes)
        if asks(scene)
    ]


def framing_problems(story: Story) -> list[str]:
    ends = (story.scenes[0], story.scenes[-1])
    if len(story.scenes) > 1 and not any(asks(scene) or reveals(scene) for scene in ends):
        return []
    return ["open with an intro scene and end with a closing scene, with no question or answer"]


def count_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    wanted, found = settings.story.quiz_questions, len(question_pairs(story))
    return [] if found == wanted else [f"ask exactly {wanted} questions, not {found}"]


def choice_problems(number: int, question: StoryScene, answer: str, wanted: int) -> list[str]:
    if len(question.choices) != wanted:
        if not wanted:
            return [f"ask question {number} as an open question, with no choices"]
        return [f"give question {number} exactly {wanted} choices"]
    offered = {choice.strip().casefold() for choice in question.choices}
    if wanted and answer and answer.strip().casefold() not in offered:
        return [f"make the answer to question {number} one of its choices"]
    return []


def reveal_problems(number: int, reveal: StoryScene | None) -> list[str]:
    if reveal is None or not reveals(reveal):
        return [f"follow question {number} with a reveal scene that gives its answer"]
    if contains_phrase(reveal.narration, reveal.answer):
        return []
    return [f"say the answer to question {number}, word for word, in its reveal"]


def pair_problems(
    number: int, question: StoryScene, reveal: StoryScene | None, wanted: int
) -> list[str]:
    marked = question.question.rstrip().endswith(QUESTION_MARKS)
    answer = reveal.answer if reveal is not None else ""
    return [
        *([] if marked else [f"end question {number} with a question mark"]),
        *reveal_problems(number, reveal),
        *choice_problems(number, question, answer, wanted),
    ]


def quiz_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    wanted = settings.story.answer_choices
    pairs = [
        problem
        for number, (question, reveal) in enumerate(question_pairs(story), start=1)
        for problem in pair_problems(number, question, reveal, wanted)
    ]
    return [*framing_problems(story), *count_problems(story, settings), *pairs]
