from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.story import StoryStage
from autotube.pipelines.narrated_video.story.checks import story_problems
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompts import story_request
from autotube.pipelines.narrated_video.structures.length import duration_target
from tests.fixtures.kids_data import StageRig, meta_of
from tests.fixtures.kids_fakes import FakeProviders
from tests.fixtures.quick_sections import QUICK_SECTIONS
from tests.fixtures.shaped_scripts import shaped_draft, shaped_writer
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, model_for

COUNTS = [
    ("list", "item_count", 3),
    ("list", "item_count", 15),
    ("countdown", "item_count", 3),
    ("countdown", "item_count", 15),
    ("quiz", "quiz_questions", 1),
    ("quiz", "quiz_questions", 10),
]
LENGTHS = ["short", "standard", "long"]
CRAMMED = {
    "story": {
        "quiz_questions": 10,
        "words_per_scene_min": {"en": 100, "ta": 8},
        "words_per_scene_max": {"en": 120, "ta": 40},
    }
}


def definition_for(structure: str, length: str, field: str, count: int) -> dict[str, Any]:
    return {"structure": structure, "length": length, "settings": {"story": {field: count}}}


def problems_of(definition: dict[str, Any]) -> dict[str, str]:
    return NarratedVideoEngine().problems(template(audience=GENERAL, definition=definition))


@pytest.mark.parametrize("length", LENGTHS)
@pytest.mark.parametrize(("structure", "field", "count"), COUNTS)
def test_every_length_and_count_saves_and_writes_a_passing_script(
    tmp_path: Path, structure: str, field: str, count: int, length: str
) -> None:
    definition = definition_for(structure, length, field, count)
    assert problems_of(definition) == {}
    model = model_for(KIDS, **definition)
    settings = model.model_validate(QUICK_SECTIONS)
    sample = Story.model_validate({**shaped_draft(settings), "language": "en"})
    assert story_problems(sample, settings) == []
    rig = StageRig(
        tmp_path, settings=settings, providers=FakeProviders(writer=shaped_writer(settings))
    )
    assert rig.run(StoryStage()).provider != "bundled"
    assert {item.language for item in meta_of(rig, "story")} == {"en", "ta"}


@pytest.mark.parametrize(
    ("structure", "length", "seconds"),
    [("list", "short", (68, 22)), ("list", "standard", (153, 72)), ("quiz", "long", (300, 100))],
)
def test_a_fixed_structure_derives_its_length_from_scenes_and_words(
    structure: str, length: str, seconds: tuple[int, int]
) -> None:
    settings = model_for(GENERAL, structure=structure, length=length)()
    assert duration_target(settings, "en") == seconds
    prompt = story_request(settings, "a topic", "en").prompt
    scenes = 10 if structure == "quiz" else 9
    assert f"- Exactly {scenes} scenes.\n" in prompt
    assert f"in about {seconds[0]} seconds" in prompt


def test_an_impossible_length_is_refused_at_save_and_in_the_settings() -> None:
    found = problems_of({"structure": "quiz", "settings": CRAMMED})
    assert list(found) == ["definition.length"]
    assert "22 scenes read in 1100 to 1320 s in English" in found["definition.length"]
    assert "choose another length or count" in found["definition.length"]
    with pytest.raises(ValidationError, match="choose another length or count"):
        model_for(GENERAL, structure="quiz").model_validate(CRAMMED)


def test_a_story_keeps_its_configured_length() -> None:
    settings = KidsStorySettings()
    assert duration_target(settings, "en") == (150, 30)
    assert "- Between 8 and 10 scenes.\n" in story_request(settings, "sharing", "en").prompt


def test_invalid_settings_are_reported_without_a_length_problem() -> None:
    found = problems_of({"structure": "list", "settings": {"story": {"item_count": 99}}})
    assert "definition.length" not in found
    assert any(path.startswith("definition.settings") for path in found)
