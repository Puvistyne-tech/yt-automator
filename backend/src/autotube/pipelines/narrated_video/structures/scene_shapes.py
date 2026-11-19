from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.structures.list_checks import expected_numbers
from autotube.pipelines.narrated_video.structures.spec import Schema

SOME_TEXT: Schema = {"type": "string", "minLength": 1}
NO_TEXT: Schema = {"type": "string", "maxLength": 0}
NO_NUMBER: Schema = {"type": "null"}


def framed(inner: list[Schema], frame: Schema) -> list[Schema]:
    return [frame, *inner, frame]


def item_shape(number: int) -> Schema:
    return {"number": {"type": "integer", "const": number}, "heading": SOME_TEXT}


def list_shapes(settings: KidsStorySettings, descending: bool) -> list[Schema]:
    numbers = expected_numbers(settings.story.item_count, descending)
    frame = {"number": NO_NUMBER, "heading": NO_TEXT}
    return framed([item_shape(number) for number in numbers], frame)


def choice_list(count: int) -> Schema:
    return {"type": "array", "items": SOME_TEXT, "minItems": count, "maxItems": count}


def quiz_shapes(settings: KidsStorySettings) -> list[Schema]:
    ask = {
        "question": SOME_TEXT,
        "answer": NO_TEXT,
        "choices": choice_list(settings.story.answer_choices),
    }
    reveal = {"question": NO_TEXT, "answer": SOME_TEXT}
    pairs = [shape for _ in range(settings.story.quiz_questions) for shape in (ask, reveal)]
    return framed(pairs, {"question": NO_TEXT, "answer": NO_TEXT})
