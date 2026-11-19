from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.story import ScriptUnavailableError, StoryStage
from tests.fixtures.kids_data import StageRig, is_translation, meta_of
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, as_json
from tests.fixtures.script_builders import scripted_draft
from tests.fixtures.shaped_scripts import narration, shaped_draft, shaped_text
from tests.fixtures.template_settings import GENERAL, model_for

ENGINE = NarratedVideoEngine()
HISTORY = next(item for item in ENGINE.builtin_templates() if item.id == "history_in_five_minutes")
TAKEAWAY = "The compass let sailors find their way without seeing land."
HOOK = "How did a small needle change the way people travelled?"
SCENES = 16
MIDDLE = 8
SEA = "Sailors watched the sea."
DEAD = "The old maps were dead wrong."
SHORT = (25, "")


def history_settings() -> KidsStorySettings:
    settings = ENGINE.pipeline(HISTORY).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def history_draft(words: int, moral: str = TAKEAWAY, middle: str = SEA) -> dict[str, Any]:
    lines = [narration(HOOK, words), *(narration(SEA, words) for _ in range(SCENES - 1))]
    lines[MIDDLE] = narration(middle, words)
    return {**scripted_draft("The Compass", lines, [{}] * SCENES), "moral": moral}


def queued_writer(answers: list[dict[str, Any]]) -> FakeWriter:
    queue = list(answers)

    def respond(request: TextRequest) -> str:
        return as_json(history_text() if is_translation(request) else queue.pop(0))

    return FakeWriter(respond)


def history_rig(tmp_path: Path, answers: list[dict[str, Any]]) -> tuple[StageRig, FakeWriter]:
    writer = queued_writer(answers)
    rig = StageRig(tmp_path, settings=history_settings(), providers=FakeProviders(writer=writer))
    return rig, writer


def history_text() -> dict[str, Any]:
    lines = ["ஒரு சிறிய ஊசி பயணத்தை எப்படி மாற்றியது?", *["மாலுமிகள் கடலைப் பார்த்தார்கள்."] * (SCENES - 2)]
    takeaway = "திசைகாட்டி நிலம் தெரியாமலே மாலுமிகளுக்கு வழி காட்டியது."
    return {
        "title": "திசைகாட்டி",
        "moral": takeaway,
        "narrations": [*lines, f"நினைவில் கொள்ளுங்கள்: {takeaway}"],
    }


def writer_of(
    script: Callable[[], dict[str, Any]], text: Callable[[], dict[str, Any]]
) -> FakeWriter:
    def respond(request: TextRequest) -> str:
        return as_json(text() if is_translation(request) else script())

    return FakeWriter(respond)


def written_by(tmp_path: Path, settings: KidsStorySettings, writer: FakeWriter) -> StageRig:
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    assert rig.run(StoryStage()).provider == "fake-llm"
    assert {item.language for item in meta_of(rig, "story")} == {"en", "ta"}
    return rig


def test_the_history_run_from_the_mac_ends_accepted(tmp_path: Path) -> None:
    answers = [history_draft(*SHORT), history_draft(38, middle=DEAD), history_draft(38)]
    rig, writer = history_rig(tmp_path, answers)
    assert rig.run(StoryStage()).provider == "fake-llm"
    first, second = [request for request in writer.requests if not is_translation(request)]
    assert "between 510 and 690 words in total" in first.prompt
    assert "too short: 400 words, need at least 510" in second.prompt
    assert "Edit it instead of starting over" in second.prompt and f'"{SEA}' in second.prompt
    rejected = "story attempt 1 failed checks (400 words, 16 scenes, about 200 s)"
    assert any(rejected in line for line in rig.logs)
    record = json.loads((tmp_path / "story" / "attempt-1-en.json").read_text(encoding="utf-8"))
    assert 'write the takeaway in "moral"' in record["failed_checks"]
    assert not (tmp_path / "story" / "attempt-2-en.json").exists()
    assert "dead" not in " ".join(rig.logs)
    assert any(
        "story attempt 2 passed after repair: added the takeaway" in line for line in rig.logs
    )
    english = (tmp_path / "story" / "story-en.json").read_text(encoding="utf-8")
    assert DEAD in english and english.count(TAKEAWAY) >= 2


def test_three_short_history_scripts_fail_with_their_measured_checks(tmp_path: Path) -> None:
    rig, _ = history_rig(tmp_path, [history_draft(*SHORT)] * 3)
    with pytest.raises(ScriptUnavailableError, match="never falls back") as raised:
        rig.run(StoryStage())
    message = str(raised.value)
    assert "; the last story attempt 3 failed checks (400 words, 16 scenes, about 200 s)" in message
    assert "too short: 400 words, need at least 510" in message
    assert 'write the takeaway in "moral"' in message


def numbers_swapped(settings: KidsStorySettings) -> dict[str, Any]:
    draft = shaped_draft(settings)
    scenes = draft["scenes"]
    scenes[1]["number"], scenes[2]["number"] = scenes[2]["number"], scenes[1]["number"]
    return draft


def question_unmarked(settings: KidsStorySettings) -> dict[str, Any]:
    draft = shaped_draft(settings)
    draft["scenes"][1]["question"] = draft["scenes"][1]["question"].rstrip("?")
    return draft


@pytest.mark.parametrize(
    ("structure", "slip", "note"),
    [
        ("list", numbers_swapped, "numbered the list items in order"),
        ("countdown", numbers_swapped, "numbered the list items in order"),
        ("quiz", question_unmarked, "ended every quiz question with a question mark"),
    ],
)
def test_a_slightly_off_general_script_ends_accepted(
    tmp_path: Path,
    structure: str,
    slip: Callable[[KidsStorySettings], dict[str, Any]],
    note: str,
) -> None:
    settings = model_for(GENERAL, structure=structure)()
    writer = writer_of(lambda: slip(settings), lambda: shaped_text(settings))
    rig = written_by(tmp_path, settings, writer)
    assert any(note in line for line in rig.logs)
