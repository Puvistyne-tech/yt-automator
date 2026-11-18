from __future__ import annotations

import pytest

from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.authoring import StoryAuthor, WriterUnavailableError
from automator.pipelines.kids_story.story.model import Story, StoryDraft
from automator.pipelines.kids_story.story.parsing import StoryFormatError, parse_model
from automator.pipelines.kids_story.story.prompts import story_request, translation_request
from automator.pipelines.kids_story.story.shaping import shaped
from tests.fixtures.kids_data import draft_dict, quick_settings, story, tamil_text
from tests.fixtures.kids_fakes import LogBook, as_json, failing_writer, scripted_writer

SETTINGS = KidsStorySettings()


def test_story_prompt_reflects_settings_and_feedback() -> None:
    settings = quick_settings(
        story={"scene_count_min": 5, "scene_count_max": 6, "temperature": 1.1}
    )
    request = story_request(settings, "being patient", "en", ["fix scene 2"])
    assert "Between 5 and 6 scenes" in request.prompt and "being patient" in request.prompt
    assert "- fix scene 2" in request.prompt and request.temperature == 1.1
    assert 'id "kavin": Kavin, a baby elephant' in request.prompt
    assert "Be kind, be brave, be you!" in request.prompt
    assert "No violence" in request.system and "aged 3 to 7" in request.system
    assert request.json_schema is not None and request.json_schema["title"] == "StoryDraft"


def test_translation_prompt_keeps_structure() -> None:
    request = translation_request(SETTINGS, story(), "en", "ta")
    assert "exactly 9 narrations" in request.prompt and "Kavin = கவின்" in request.prompt
    assert "அன்பாக இரு, துணிவாக இரு, நீயாகவே இரு!" in request.prompt
    assert request.temperature == SETTINGS.story.translation_temperature


def test_parse_model_accepts_fenced_json_and_reports_problems() -> None:
    parsed = parse_model("```json\n" + as_json(draft_dict()) + "\n```", StoryDraft)
    assert parsed.title == "Kavin and the Golden Mango"
    with pytest.raises(StoryFormatError, match="one JSON object"):
        parse_model("no json here", Story)
    with pytest.raises(StoryFormatError, match="invalid"):
        parse_model("{not json}", Story)
    with pytest.raises(StoryFormatError, match="shape"):
        parse_model('{"title": "x"}', Story)


def test_author_retries_with_feedback_then_succeeds() -> None:
    bad = {**draft_dict(), "scenes": draft_dict()["scenes"][:3]}
    writer = scripted_writer([as_json(bad), "nonsense", as_json(draft_dict())])
    logs = LogBook()
    written = StoryAuthor(writer, SETTINGS, logs).written("sharing", "en")
    assert written is not None and written.title == "Kavin and the Golden Mango"
    assert "use between 8 and 10 scenes, not 3" in writer.requests[1].prompt
    assert "answer with one JSON object" in writer.requests[2].prompt
    assert len(logs.lines) == 2


@pytest.mark.parametrize("attempts", [1, 2])
def test_author_gives_up_after_max_attempts(attempts: int) -> None:
    settings = quick_settings(story={"max_attempts": attempts})
    writer = scripted_writer(["x", "y", as_json(draft_dict())])
    assert StoryAuthor(writer, settings, LogBook()).written("sharing", "en") is None
    assert len(writer.requests) == attempts


def test_each_retry_carries_only_the_latest_feedback() -> None:
    few_scenes = {**draft_dict(), "scenes": draft_dict()["scenes"][:3]}
    writer = scripted_writer([as_json(few_scenes), "nonsense", as_json(draft_dict())])
    StoryAuthor(writer, SETTINGS, LogBook()).written("sharing", "en")
    assert "answer with one JSON object" in writer.requests[2].prompt
    assert "not 3" not in writer.requests[2].prompt


def test_author_reports_a_shape_problem_and_accepts_fenced_json() -> None:
    fenced = "```json\n" + as_json(draft_dict()) + "\n```"
    writer = scripted_writer([as_json({**draft_dict(), "scenes": []}), fenced])
    written = StoryAuthor(writer, SETTINGS, LogBook()).written("sharing", "en")
    assert written is not None and written.title == "Kavin and the Golden Mango"
    assert "does not match the shape" in writer.requests[1].prompt


def test_author_translation_and_unavailable_writer() -> None:
    writer = scripted_writer(
        [as_json({**tamil_text(), "narrations": ["ஒன்று"]}), as_json(tamil_text())]
    )
    translated = StoryAuthor(writer, SETTINGS, LogBook()).translated(story(), "ta")
    assert translated is not None and translated.language == "ta"
    assert translated.scenes[0].visual == story().scenes[0].visual
    with pytest.raises(WriterUnavailableError):
        StoryAuthor(failing_writer(), SETTINGS, LogBook()).written("sharing", "en")


def test_shaping_limits_heroes_questions_and_short_scenes() -> None:
    scenes = [scene.model_copy(update={"hero": True}) for scene in story().scenes]
    raw = story(questions=["a", "b", "c"], short_scenes=[0, 0, 42, 3])
    shaped_story = shaped(raw.model_copy(update={"scenes": scenes}), SETTINGS)
    assert sum(scene.hero for scene in shaped_story.scenes) == 2
    assert shaped_story.questions == ["a", "b"] and shaped_story.short_scenes == [0, 3]
