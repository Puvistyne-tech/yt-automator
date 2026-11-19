from __future__ import annotations

from collections.abc import Callable
from typing import Any

from autotube.domain.capabilities import TextRequest
from tests.fixtures.kids_data import is_judge, is_translation
from tests.fixtures.kids_fakes import FakeWriter, as_json

Labels = dict[str, Any]
Draft = Callable[[], dict[str, Any]]


def scripted_scene(narration: str, index: int, labels: Labels) -> dict[str, Any]:
    return {
        "narration": narration,
        "visual": f"a sunny meadow full of flowers, view {index + 1}",
        "action": "A honeybee lands softly on a yellow flower.",
        "characters": [],
        "setting": "a sunny meadow",
        "mood": "bright and calm",
        "camera": "push_in",
        "hero": index in (2, 5),
        "sound_effects": [],
        "speaker": "narrator",
        **labels,
    }


def scripted_draft(title: str, narrations: list[str], labels: list[Labels]) -> dict[str, Any]:
    scenes = [
        scripted_scene(line, index, label)
        for index, (line, label) in enumerate(zip(narrations, labels, strict=True))
    ]
    return {
        "title": title,
        "scenes": scenes,
        "questions": ["Which part did you like best?", "What would you like to learn next?"],
        "short_scenes": [0, 1, 2],
        "hook_line": "Here is something new to learn today.",
        "thumbnail": "a bright meadow full of flowers under a clear blue sky",
    }


def scripted_text(title: str, narrations: list[str], labels: list[Labels]) -> dict[str, Any]:
    return {
        "title": title,
        "narrations": narrations,
        "questions": ["உங்களுக்கு எது பிடித்தது?", "அடுத்து எதைக் கற்க விரும்புகிறீர்கள்?"],
        "hook_line": "இன்று புதிதாக ஒன்றைக் கற்போம்.",
        "scene_labels": labels,
    }


def scripted_writer(draft: Draft, text: Draft, judge_answer: str = "1") -> FakeWriter:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return judge_answer
        return as_json(text() if is_translation(request) else draft())

    return FakeWriter(respond)
