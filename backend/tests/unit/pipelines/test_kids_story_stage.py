from __future__ import annotations

from pathlib import Path
from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.kids_story.stages.story import StoryStage
from autotube.pipelines.kids_story.story.authoring import StoryAuthor
from tests.fixtures.kids_data import (
    StageRig,
    english_text,
    is_translation,
    meta_of,
    quick_settings,
    story,
    story_answer,
    tamil_draft,
    tamil_text,
)
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, LogBook, as_json, scripted_writer


def tamil_without_moral() -> dict[str, Any]:
    text = tamil_text()
    return {**text, "narrations": [*text["narrations"][:-1], "கவின் சிரித்தான்."]}


def tamil_with_banned_word() -> dict[str, Any]:
    text = tamil_text()
    return {**text, "narrations": [f"monster {text['narrations'][0]}", *text["narrations"][1:]]}


def test_translation_missing_the_moral_is_retried_then_dropped() -> None:
    settings = quick_settings(story={"max_attempts": 2})
    writer = scripted_writer([as_json(tamil_without_moral())] * 2)
    logs = LogBook()
    assert StoryAuthor(writer, settings, logs).translated(story(), "ta") is None
    assert len(writer.requests) == 2
    assert logs.lines[0].startswith("translation to ta attempt 1 failed: say the moral")


def test_translation_runs_the_safety_gates() -> None:
    writer = scripted_writer([as_json(tamil_with_banned_word()), as_json(tamil_text())])
    logs = LogBook()
    translated = StoryAuthor(writer, quick_settings(), logs).translated(story(), "ta")
    assert translated is not None and len(writer.requests) == 2
    assert "remove these words: monster" in logs.lines[0]


def test_a_single_translation_attempt_asks_once() -> None:
    settings = quick_settings(story={"max_attempts": 1})
    writer = scripted_writer([as_json(tamil_without_moral()), as_json(tamil_text())])
    assert StoryAuthor(writer, settings, LogBook()).translated(story(), "ta") is None
    assert len(writer.requests) == 1


def stage_rig(root: Path, writer: FakeWriter, **story_settings: object) -> StageRig:
    settings = quick_settings(story={"max_attempts": 2, **story_settings})
    return StageRig(root, settings=settings, providers=FakeProviders(writer=writer))


def test_writer_failing_during_translation_falls_back_for_every_language(tmp_path: Path) -> None:
    def respond(request: TextRequest) -> str:
        if is_translation(request):
            raise RuntimeError("model went away")
        return story_answer()

    rig = stage_rig(tmp_path, FakeWriter(respond))
    assert rig.run(StoryStage()).provider == "bundled"
    assert {(item.language, item.meta["source"]) for item in meta_of(rig, "story")} == {
        ("en", "bundled"),
        ("ta", "bundled"),
    }
    assert any("story writer unavailable: model went away" in line for line in rig.logs)
    assert any("falling back" in line for line in rig.logs)


def test_translation_that_never_passes_falls_back(tmp_path: Path) -> None:
    writer = scripted_writer([story_answer(), *[as_json(tamil_without_moral())] * 2])
    rig = stage_rig(tmp_path, writer)
    assert rig.run(StoryStage()).provider == "bundled"
    assert {item.meta["source"] for item in meta_of(rig, "story")} == {"bundled"}


def test_invalid_answers_forever_fall_back_after_every_attempt(tmp_path: Path) -> None:
    writer = scripted_writer(["not json"] * 3)
    rig = stage_rig(tmp_path, writer, max_attempts=3)
    assert rig.run(StoryStage()).provider == "bundled" and len(writer.requests) == 3


def test_tamil_first_stories_are_translated_into_english(tmp_path: Path) -> None:
    def respond(request: TextRequest) -> str:
        return as_json(english_text()) if is_translation(request) else as_json(tamil_draft())

    writer = FakeWriter(respond)
    rig = stage_rig(tmp_path, writer, primary_language="ta")
    assert rig.run(StoryStage()).provider == "fake-llm"
    first, second = writer.requests
    assert "Tamil" in first.prompt and not is_translation(first)
    assert is_translation(second) and "from Tamil" in second.prompt
    assert [(item.language, item.meta["source"]) for item in meta_of(rig, "story")] == [
        ("ta", "llm"),
        ("en", "llm"),
    ]


def test_tamil_only_runs_write_in_tamil(tmp_path: Path) -> None:
    writer = FakeWriter(lambda _request: as_json(tamil_draft()))
    rig = stage_rig(tmp_path, writer)
    rig.languages = ("ta",)
    rig.run(StoryStage())
    assert [item.language for item in meta_of(rig, "story")] == ["ta"]
    assert len(writer.requests) == 1 and not is_translation(writer.requests[0])
