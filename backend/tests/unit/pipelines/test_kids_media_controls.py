from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from autotube.pipelines.narrated_video.art.prompts import judge_request, motion_prompt
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.settings.legacy_motion import LEGACY_MOTION_PROMPTS
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.music import bed_prompt
from autotube.pipelines.narrated_video.stages.voice import Line, speech_request
from autotube.pipelines.narrated_video.story.model import StoryScene
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, run_chain
from tests.fixtures.kids_fakes import FakeProviders

SCHEMA = KidsStorySettings.model_json_schema()
SCENE = StoryScene(narration="Hi.", visual="a fox", mood="sleepy")


@pytest.mark.parametrize(
    ("stored", "expected"),
    [(0.8, (0.8, 0.8)), (1, (1.0, 1.0)), ({"en": 1.2}, (1.2, 0.95)), (0.5, (0.5, 0.5))],
)
def test_stored_speeds_load_for_every_language(
    stored: object, expected: tuple[float, float]
) -> None:
    speed = quick_settings(voice={"speed": stored}).voice.speed
    assert (speed.for_language("en"), speed.for_language("ta")) == expected


def test_speed_boundaries_are_accepted() -> None:
    speed = quick_settings(voice={"speed": {"en": 0.5, "ta": 1.5}}).voice.speed
    assert (speed.for_language("en"), speed.for_language("ta")) == (0.5, 1.5)


def test_speed_per_language_reaches_each_speech_request() -> None:
    settings = quick_settings(voice={"speed": {"en": 1.1, "ta": 0.7}})
    line = Line("scene-0", "Hello there.")
    assert speech_request(settings, line, "en").speed == 1.1
    assert speech_request(settings, line, "ta").speed == 0.7


@pytest.mark.parametrize("speed", [0.2, 0.49, 1.51, {"en": 1.0, "ta": 2.0}, True])
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


def test_the_music_stage_uses_the_short_mood_only_for_short_beds(tmp_path: Path) -> None:
    settings = quick_settings(
        music={"mood_prompt": "harp", "short_mood_prompt": "bouncy"},
        sound_effects={"enabled": False},
    )
    providers = FakeProviders()
    rig = run_chain(StageRig(tmp_path, settings=settings, providers=providers), "music")
    assert providers.music is not None
    beds = zip(meta_of(rig, "music"), providers.music.requests, strict=True)
    by_variant = {(bed.language, bed.variant, request.prompt) for bed, request in beds}
    assert by_variant == {
        ("en", "episode", "harp"),
        ("ta", "episode", "harp"),
        ("en", "short", "bouncy"),
        ("ta", "short", "bouncy"),
    }


def test_the_motion_prompt_setting_fills_scene_and_card_placeholders() -> None:
    settings = quick_settings(visuals={"motion_prompt": "Cost $5 {Visual} {} {visual}, {mood}"})
    assert motion_prompt(settings, SCENE).endswith(". Cost $5 {Visual} {} a fox, sleepy")
    assert motion_prompt(settings, None, "drift").endswith(
        ". Cost $5 {Visual} {} a title card, warm Camera: drift."
    )


def test_an_unknown_motion_placeholder_is_rejected_naming_the_field() -> None:
    with pytest.raises(
        ValidationError, match=r"motion_prompt[\s\S]*unknown: \{colour\}, \{other\}"
    ):
        quick_settings(visuals={"motion_prompt": "{action} {visual} {other} {colour}"})


def test_the_default_motion_prompt_leads_with_the_scene_action() -> None:
    scene = SCENE.model_copy(update={"action": "The fox curls up and yawns. "})
    scene_part = "The fox curls up and yawns. Mood: sleepy. Gentle, slow movement"
    assert scene_part in motion_prompt(quick_settings(), scene)


def test_a_scene_without_an_action_animates_its_visual_once() -> None:
    scene = SCENE.model_copy(update={"visual": "a fox naps."})
    prompt = motion_prompt(quick_settings(), scene)
    assert "a fox naps. Mood: sleepy. Gentle" in prompt
    assert prompt.count("a fox naps") == 1 and ".." not in prompt


def test_a_card_motion_prompt_reveals_the_title_card() -> None:
    settings = quick_settings(visuals={"motion_prompt": "{action}: {visual}, {mood}."})
    assert motion_prompt(settings, None).endswith(
        ". A gentle title card reveal: a title card, warm."
    )


@pytest.mark.parametrize(("legacy", "upgraded"), list(LEGACY_MOTION_PROMPTS.items()))
def test_a_stored_legacy_default_motion_prompt_gains_the_action(legacy: str, upgraded: str) -> None:
    visuals = quick_settings(visuals={"motion_prompt": legacy}).visuals
    assert visuals.motion_prompt == upgraded and "{action}" in upgraded


def test_the_judge_criteria_setting_reaches_the_judge(tmp_path: Path) -> None:
    settings = quick_settings(visuals={"judge_criteria": "Pick $count funny {visual} {}."})
    prompt = judge_request(settings, SCENE, [tmp_path]).prompt
    assert "in the order given. Pick $count funny {visual} {}.\nAnswer with only" in prompt


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
        "structure",
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
