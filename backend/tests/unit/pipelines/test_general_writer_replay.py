from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.story import StoryStage
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


def history_settings() -> KidsStorySettings:
    settings = ENGINE.pipeline(HISTORY).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def history_draft(words: int) -> dict[str, Any]:
    lines = [
        narration(HOOK, words),
        *(narration("Sailors watched the sea.", words) for _ in range(SCENES - 1)),
    ]
    return {**scripted_draft("The Compass", lines, [{}] * SCENES), "moral": TAKEAWAY}


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


def test_a_long_history_explainer_without_its_spoken_takeaway_is_repaired(tmp_path: Path) -> None:
    settings = history_settings()
    writer = writer_of(lambda: history_draft(38), history_text)
    rig = written_by(tmp_path, settings, writer)
    assert "between 510 and 690 words in total" in writer.requests[0].prompt
    assert any("added the takeaway to the last scene" in line for line in rig.logs)


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
