from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.narrated_video.stages.story import StoryStage
from autotube.pipelines.narrated_video.story.answer_schema import draft_schema
from autotube.pipelines.narrated_video.story.attempts import attempt_record
from autotube.pipelines.narrated_video.story.authoring import StoryAuthor
from tests.fixtures.kids_data import REFRAIN_EN, StageRig, is_translation, meta_of, quick_settings
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, LogBook, as_json, scripted_writer
from tests.fixtures.mac_runs import mac_settings
from tests.fixtures.script_builders import scripted_draft
from tests.fixtures.shaped_scripts import narration

MORAL = "Sharing makes everyone happier."
SCENES = 5
REFRAIN_TA = quick_settings().series.refrain.ta
MORAL_TA = "பகிர்ந்தால் எல்லோருக்கும் மகிழ்ச்சி."


def draft(words_per_scene: int, moral: str) -> dict[str, Any]:
    lines = [narration("Kavin found a mango.", words_per_scene) for _ in range(SCENES)]
    written = scripted_draft("Kavin Shares", lines, [{}] * SCENES)
    return {**written, "moral": moral}


def tamil_text() -> dict[str, Any]:
    lines = ["கவின் ஒரு மாம்பழம் கண்டான்."] * (SCENES - 1)
    closing = f"கவின் சிரித்தான். {MORAL_TA} {REFRAIN_TA}"
    return {"title": "கவின் பகிர்கிறான்", "moral": MORAL_TA, "narrations": [*lines, closing]}


def replay_writer(answers: list[dict[str, Any]]) -> FakeWriter:
    queue = list(answers)

    def respond(request: TextRequest) -> str:
        return as_json(tamil_text() if is_translation(request) else queue.pop(0))

    return FakeWriter(respond)


def story_requests(writer: FakeWriter) -> list[TextRequest]:
    return [request for request in writer.requests if not is_translation(request)]


def test_the_mac_failure_pattern_now_ends_in_a_written_story(tmp_path: Path) -> None:
    writer = replay_writer([draft(34, ""), draft(24, MORAL)])
    rig = StageRig(tmp_path, settings=mac_settings(), providers=FakeProviders(writer=writer))
    outcome = rig.run(StoryStage())
    first, second = story_requests(writer)
    assert first.json_schema == draft_schema(mac_settings())
    assert "between 80 and 160 words in total" in first.prompt
    assert "between 20 and 26 words" in first.prompt
    assert "too long: 170 words, use at most 160" in second.prompt
    assert 'write the moral in "moral"' in second.prompt and "Edit it" in second.prompt
    assert outcome.provider == "fake-llm" and "bundled" not in " ".join(rig.logs)
    assert any("story attempt 2 passed after repair" in line for line in rig.logs)
    english = (tmp_path / "story" / "story-en.json").read_text(encoding="utf-8")
    assert f"{MORAL} {REFRAIN_EN}" in english
    assert {item.language for item in meta_of(rig, "story")} == {"en", "ta"}


def test_a_rejected_attempt_is_logged_with_its_measures_and_kept_in_the_workspace(
    tmp_path: Path,
) -> None:
    writer = replay_writer([draft(34, ""), draft(24, MORAL)])
    rig = StageRig(tmp_path, settings=mac_settings(), providers=FakeProviders(writer=writer))
    rig.run(StoryStage())
    assert any(
        "story attempt 1 failed checks (170 words, 5 scenes, about 85 s)" in line
        for line in rig.logs
    )
    record = json.loads((tmp_path / "story" / "attempt-1-en.json").read_text(encoding="utf-8"))
    assert set(record) == {"attempt", "language", "failed_checks", "script"}
    assert "too long: 170 words, use at most 160" in record["failed_checks"][0]
    assert record["script"]["moral"] == "" and len(record["script"]["scenes"]) == SCENES
    assert not (tmp_path / "story" / "attempt-2-en.json").exists()


def test_an_unreadable_answer_is_kept_as_text() -> None:
    kept: list[dict[str, Any]] = []
    settings = mac_settings(max_attempts=1)
    writer = scripted_writer(["no json here"])
    author = StoryAuthor(
        writer, settings, LogBook(), keep=lambda attempt: kept.append(attempt_record(attempt))
    )
    assert author.written("sharing", "en") is None
    assert kept == [
        {
            "attempt": 1,
            "language": "en",
            "failed_checks": ["answer with one JSON object"],
            "answer": "no json here",
        }
    ]
    assert "an answer of 12 characters that is not a script" in author.failures[-1]


def test_without_repair_the_same_answers_fall_back(tmp_path: Path) -> None:
    writer = replay_writer([draft(34, ""), draft(24, MORAL), draft(24, MORAL)])
    settings = mac_settings(repair_slips=False)
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    assert rig.run(StoryStage()).provider == "bundled"


def test_a_repair_that_breaks_the_length_still_fails_the_attempt() -> None:
    full = draft(26, MORAL)
    settings = mac_settings(
        target_duration_seconds=65, duration_tolerance_seconds=0, max_attempts=1
    )
    logs = LogBook()
    assert StoryAuthor(replay_writer([full]), settings, logs).written("sharing", "en") is None
    assert not any("passed after repair" in line for line in logs.lines)
    assert "the moral, word for word" in logs.lines[-1]
