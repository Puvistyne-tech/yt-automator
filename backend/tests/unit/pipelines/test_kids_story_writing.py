from __future__ import annotations

from typing import Any

import pytest

from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.authoring import StoryAuthor, WriterUnavailableError
from automator.pipelines.kids_story.story.gates import (
    banned_word_problems,
    brand_problems,
    cast_problems,
    duration_problems,
    ending_problems,
    reading_level_problems,
    scene_count_problems,
    story_problems,
    words_per_scene_problems,
)
from automator.pipelines.kids_story.story.model import Story, StoryDraft
from automator.pipelines.kids_story.story.parsing import StoryFormatError, parse_model
from automator.pipelines.kids_story.story.prompts import story_request, translation_request
from automator.pipelines.kids_story.story.shaping import shaped
from tests.unit.pipelines.kids_data import draft_dict, quick_settings, tamil_text
from tests.unit.pipelines.kids_fakes import as_json, failing_writer, scripted_writer

SETTINGS = KidsStorySettings()


def story(**changes: Any) -> Story:
    return Story.model_validate({**draft_dict(), "language": "en", "theme": "sharing", **changes})


def with_narration(index: int, text: str) -> Story:
    good = story()
    scenes = list(good.scenes)
    scenes[index] = scenes[index].model_copy(update={"narration": text})
    return good.model_copy(update={"scenes": scenes})


def test_a_good_story_passes_every_gate() -> None:
    assert story_problems(story(), SETTINGS) == []


def test_scene_count_gate_follows_settings() -> None:
    assert scene_count_problems(story(), SETTINGS) == []
    tight = quick_settings(story={"scene_count_min": 10, "scene_count_max": 12})
    assert scene_count_problems(story(), tight) == ["use between 10 and 12 scenes, not 9"]


def test_words_per_scene_gate() -> None:
    short = with_narration(2, "Kutty smiled.")
    assert words_per_scene_problems(short, SETTINGS) == [
        "scene 3 has 2 words; use between 18 and 50"
    ]


def test_duration_gate() -> None:
    assert duration_problems(story(), SETTINGS) == []
    quick = quick_settings(story={"target_duration_seconds": 60, "duration_tolerance_seconds": 5})
    assert "aim for 60 s" in duration_problems(story(), quick)[0]


def test_ending_gate_needs_moral_and_refrain() -> None:
    ending = "Kutty felt warm and bright inside and smiled at all of his dear friends."
    problems = ending_problems(with_narration(8, ending), SETTINGS)
    assert len(problems) == 2
    changed = quick_settings(series={"refrain": {"en": "Hooray!", "ta": "ஆஹா!"}})
    assert ending_problems(story(), changed) == ['end the last scene with the refrain "Hooray!"']


def test_banned_words_and_brands_are_found() -> None:
    bad = with_narration(1, "The monster drank a Pepsi under the tree and felt very happy today.")
    assert banned_word_problems(bad, SETTINGS) == ["remove these words: monster"]
    assert brand_problems(bad, SETTINGS) == ["remove these brand names: Pepsi"]


def test_reading_level_gate() -> None:
    assert reading_level_problems(story(), SETTINGS) == []
    strict = quick_settings(
        story={
            "max_average_sentence_words": {"en": 4, "ta": 4},
            "long_word_graphemes": {"en": 6, "ta": 6},
            "max_long_word_share": 0.0,
        }
    )
    assert reading_level_problems(story(), strict) == [
        "use shorter sentences: at most 4 words on average",
        "use fewer long words",
    ]


def test_cast_gate() -> None:
    scenes = [scene.model_copy(update={"characters": ["dragon"]}) for scene in story().scenes]
    assert cast_problems(story().model_copy(update={"scenes": scenes}), SETTINGS) == [
        "only use cast ids; unknown: dragon"
    ]


def test_story_prompt_reflects_settings_and_feedback() -> None:
    settings = quick_settings(
        story={"scene_count_min": 5, "scene_count_max": 6, "temperature": 1.1}
    )
    request = story_request(settings, "being patient", "en", ["fix scene 2"])
    assert "Between 5 and 6 scenes" in request.prompt and "being patient" in request.prompt
    assert "- fix scene 2" in request.prompt and request.temperature == 1.1
    assert 'id "kutty": Kutty, a baby elephant' in request.prompt
    assert "Be kind, be brave, be you!" in request.prompt
    assert "No violence" in request.system and "aged 3 to 7" in request.system
    assert request.json_schema is not None and request.json_schema["title"] == "StoryDraft"


def test_translation_prompt_keeps_structure() -> None:
    request = translation_request(SETTINGS, story(), "en", "ta")
    assert "exactly 9 narrations" in request.prompt and "Kutty = குட்டி" in request.prompt
    assert "அன்பாக இரு, துணிவாக இரு, நீயாகவே இரு!" in request.prompt
    assert request.temperature == SETTINGS.story.translation_temperature


def test_parse_model_accepts_fenced_json_and_reports_problems() -> None:
    parsed = parse_model("```json\n" + as_json(draft_dict()) + "\n```", StoryDraft)
    assert parsed.title == "Kutty and the Golden Mango"
    with pytest.raises(StoryFormatError, match="one JSON object"):
        parse_model("no json here", Story)
    with pytest.raises(StoryFormatError, match="invalid"):
        parse_model("{not json}", Story)
    with pytest.raises(StoryFormatError, match="shape"):
        parse_model('{"title": "x"}', Story)


def test_author_retries_with_feedback_then_succeeds() -> None:
    bad = {**draft_dict(), "scenes": draft_dict()["scenes"][:3]}
    writer = scripted_writer([as_json(bad), "nonsense", as_json(draft_dict())])
    logs: list[str] = []
    written = StoryAuthor(writer, SETTINGS, logs.append).written("sharing", "en")
    assert written is not None and written.title == "Kutty and the Golden Mango"
    assert "use between 8 and 10 scenes, not 3" in writer.requests[1].prompt
    assert "answer with one JSON object" in writer.requests[2].prompt
    assert len(logs) == 2


def test_author_gives_up_after_max_attempts() -> None:
    settings = quick_settings(story={"max_attempts": 2})
    writer = scripted_writer(["x", "y", as_json(draft_dict())])
    assert StoryAuthor(writer, settings, print).written("sharing", "en") is None
    assert len(writer.requests) == 2


def test_author_translation_and_unavailable_writer() -> None:
    writer = scripted_writer(
        [as_json({**tamil_text(), "narrations": ["ஒன்று"]}), as_json(tamil_text())]
    )
    translated = StoryAuthor(writer, SETTINGS, print).translated(story(), "ta")
    assert translated is not None and translated.language == "ta"
    assert translated.scenes[0].visual == story().scenes[0].visual
    with pytest.raises(WriterUnavailableError):
        StoryAuthor(failing_writer(), SETTINGS, print).written("sharing", "en")


def test_shaping_limits_heroes_questions_and_short_scenes() -> None:
    scenes = [scene.model_copy(update={"hero": True}) for scene in story().scenes]
    raw = story(questions=["a", "b", "c"], short_scenes=[0, 0, 42, 3])
    shaped_story = shaped(raw.model_copy(update={"scenes": scenes}), SETTINGS)
    assert sum(scene.hero for scene in shaped_story.scenes) == 2
    assert shaped_story.questions == ["a", "b"] and shaped_story.short_scenes == [0, 3]
