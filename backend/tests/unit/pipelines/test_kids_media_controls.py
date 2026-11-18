from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from autotube.pipelines.kids_story.art.prompts import judge_request, motion_prompt
from autotube.pipelines.kids_story.plugin import KidsStoryPipeline
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.stages.music import bed_prompt
from autotube.pipelines.kids_story.stages.voice import Line, speech_request
from autotube.pipelines.kids_story.story.model import StoryScene
from tests.fixtures.kids_data import quick_settings

SCHEMA = KidsStorySettings.model_json_schema()
SCENE = StoryScene(narration="Hi.", visual="a fox", mood="sleepy")


def test_a_stored_single_speed_applies_to_every_language() -> None:
    speed = quick_settings(voice={"speed": 0.8}).voice.speed
    assert (speed.for_language("en"), speed.for_language("ta")) == (0.8, 0.8)


def test_speed_per_language_reaches_each_speech_request() -> None:
    settings = quick_settings(voice={"speed": {"en": 1.1, "ta": 0.7}})
    line = Line("scene-0", "Hello there.")
    assert speech_request(settings, line, "en").speed == 1.1
    assert speech_request(settings, line, "ta").speed == 0.7


@pytest.mark.parametrize("speed", [0.2, {"en": 1.0, "ta": 2.0}, True])
def test_speeds_outside_the_range_are_rejected(speed: object) -> None:
    with pytest.raises(ValidationError):
        quick_settings(voice={"speed": speed})


@pytest.mark.parametrize(
    ("short_mood", "variant", "expected"),
    [
        ("", "short", "harp"),
        ("   ", "short", "harp"),
        ("bouncy drums", "short", "bouncy drums"),
        ("bouncy drums", "episode", "harp"),
    ],
)
def test_the_short_mood_replaces_the_main_mood_only_for_shorts(
    short_mood: str, variant: str, expected: str
) -> None:
    settings = quick_settings(music={"mood_prompt": "harp", "short_mood_prompt": short_mood})
    assert bed_prompt(settings, variant) == expected


def test_the_motion_prompt_setting_fills_scene_and_card_placeholders() -> None:
    settings = quick_settings(visuals={"motion_prompt": "Bouncy {visual} feeling {mood} {other}"})
    assert motion_prompt(settings, SCENE) == "Bouncy a fox feeling sleepy {other}"
    assert motion_prompt(settings, None, "drift") == (
        "Bouncy a title card feeling warm {other} Camera: drift."
    )


def test_the_judge_criteria_setting_reaches_the_judge(tmp_path: Path) -> None:
    settings = quick_settings(visuals={"judge_criteria": "Pick the funniest picture."})
    prompt = judge_request(settings, SCENE, [tmp_path]).prompt
    assert "in the order given. Pick the funniest picture.\nAnswer with only" in prompt


def test_enabled_checks_are_offered_as_checkboxes_without_child_safety() -> None:
    field = SCHEMA["$defs"]["StorySettings"]["properties"]["enabled_checks"]
    titles = [choice["const"] for choice in field["items"]["oneOf"]]
    assert field["uniqueItems"] is True and "banned_words" not in titles
    assert titles == [
        "scene_count",
        "words_per_scene",
        "duration",
        "ending",
        "reading_level",
        "cast",
    ]
    ui = cast(dict[str, Any], KidsStoryPipeline().descriptor.ui_schema)
    assert ui["story"]["enabled_checks"] == {"ui:widget": "checkboxes"}


def test_long_texts_are_textareas_in_the_ui() -> None:
    ui = cast(dict[str, Any], KidsStoryPipeline().descriptor.ui_schema)
    for section, name in [
        ("story", "tone"),
        ("story", "writing_style"),
        ("story", "extra_instructions"),
        ("visuals", "motion_prompt"),
        ("visuals", "judge_criteria"),
        ("music", "short_mood_prompt"),
    ]:
        assert ui[section][name]["ui:widget"] == "textarea", name
