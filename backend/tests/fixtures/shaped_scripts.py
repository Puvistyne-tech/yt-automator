from __future__ import annotations

from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.structures.length import duration_target, scene_range
from tests.fixtures.kids_data import is_judge, is_translation
from tests.fixtures.kids_fakes import FakeWriter, as_json
from tests.fixtures.script_builders import Labels, scripted_draft

FILLER = ["Bees", "hum", "softly", "near", "flowers"]
INTRO = "Here are some facts."
CLOSING = "Thanks for watching today."


def sentence(words: list[str]) -> str:
    return f"{' '.join(words)}." if words else ""


def narration(lead: str, total: int) -> str:
    remaining = total - len(lead.split())
    full, rest = divmod(max(remaining, 0), len(FILLER))
    parts = [lead, *[sentence(FILLER)] * full, sentence(FILLER[:rest])]
    return " ".join(part for part in parts if part)


def item_scenes(settings: KidsStorySettings) -> list[tuple[str, Labels]]:
    count = settings.story.item_count
    numbers = (
        range(count, 0, -1)
        if settings.story.structure.value == "countdown"
        else range(1, count + 1)
    )
    return [(f"Number {n}.", {"number": n, "heading": f"Fact number {n}"}) for n in numbers]


def quiz_scenes(settings: KidsStorySettings) -> list[tuple[str, Labels]]:
    pairs = [
        [
            (f"Question {n}.", {"question": f"Which flower is number {n}?"}),
            (f"The answer is rose {n}.", {"answer": f"rose {n}"}),
        ]
        for n in range(1, settings.story.quiz_questions + 1)
    ]
    return [scene for pair in pairs for scene in pair]


def shaped_scenes(settings: KidsStorySettings) -> list[tuple[str, Labels]]:
    middle = (
        quiz_scenes(settings) if settings.story.structure.value == "quiz" else item_scenes(settings)
    )
    return [(INTRO, {}), *middle, (CLOSING, {})]


def words_per_scene(settings: KidsStorySettings, language: str) -> int:
    scenes, _ = scene_range(settings)
    target, _ = duration_target(settings, language)
    rate = settings.story.words_per_minute.for_language(language)
    low = settings.story.words_per_scene_min.for_language(language)
    high = settings.story.words_per_scene_max.for_language(language)
    return int(min(max(round(target * rate / 60 / scenes), low), high))


def shaped_draft(settings: KidsStorySettings) -> dict[str, Any]:
    words = words_per_scene(settings, "en")
    scenes = shaped_scenes(settings)
    narrations = [narration(lead, words) for lead, _ in scenes]
    return scripted_draft("Flower Facts", narrations, [labels for _, labels in scenes])


def shaped_text(settings: KidsStorySettings) -> dict[str, Any]:
    draft = shaped_draft(settings)
    labels = [
        {key: scene.get(key, "") for key in ("heading", "question", "answer")}
        for scene in draft["scenes"]
    ]
    narrations = [scene["narration"] for scene in draft["scenes"]]
    return {"title": draft["title"], "narrations": narrations, "scene_labels": labels}


def shaped_writer(settings: KidsStorySettings) -> FakeWriter:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return "1"
        return as_json(shaped_text(settings) if is_translation(request) else shaped_draft(settings))

    return FakeWriter(respond)
