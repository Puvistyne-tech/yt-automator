from __future__ import annotations

import re
from typing import Any

import pytest

from autotube.domain.ui_schema import CHOICE_SWATCHES_KEY
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.styles.library import style_ids
from autotube.pipelines.kids_story.styles.resolve import resolve_style

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
CUSTOM_LOOK: dict[str, Any] = {
    "visual_style": "custom",
    "custom_style": {"prompt": "bright paper collage", "negative_prompt": "photo"},
}


def look_for(style_id: str) -> dict[str, Any]:
    return CUSTOM_LOOK if style_id == "custom" else {"visual_style": style_id}


@pytest.mark.parametrize("style_id", [*style_ids(), "custom"])
def test_every_style_keeps_every_child_safety_exclusion(style_id: str) -> None:
    settings = KidsStorySettings.model_validate({"look": look_for(style_id)})
    resolved = resolve_style(settings).negative_prompt.casefold().split(", ")
    exclusions = settings.safety.picture_exclusions.casefold().split(", ")
    assert [term for term in exclusions if term not in resolved] == []


@pytest.mark.parametrize("style_id", style_ids())
def test_every_library_style_resolves(style_id: str) -> None:
    style = resolve_style(KidsStorySettings.model_validate({"look": look_for(style_id)}))
    hints = style.hints()
    assert style.style_id == style_id and style.prompt.strip()
    assert 4 <= len(hints.palette) <= 6
    assert 0 <= style.motion.intensity <= style.motion.hero_intensity <= 1
    assert style.motion.held_frame_rate is None or 1 <= style.motion.held_frame_rate <= 30
    assert style.motion.feel.strip()
    assert HEX.match(style.lettering.text) and HEX.match(style.lettering.outline)


def test_every_style_card_swatch_is_a_hex_colour() -> None:
    schema = KidsStorySettings.model_json_schema()
    entries = schema["$defs"]["LookSettings"]["properties"]["visual_style"]["oneOf"]
    swatches = [colour for entry in entries for colour in entry.get(CHOICE_SWATCHES_KEY, [])]
    assert swatches and [colour for colour in swatches if not HEX.match(colour)] == []


@pytest.mark.parametrize(
    ("look", "night"),
    [
        ({}, False),
        ({"lighting": "moonlight"}, True),
        ({"colour_mood": "night"}, True),
        ({"lighting": "golden_hour", "colour_mood": "warm"}, False),
        ({"extra_prompt": "stars, dream, sleep, bedtime"}, False),
        ({**CUSTOM_LOOK, "custom_style": {"prompt": "a starry night sky"}}, False),
    ],
)
def test_only_moonlight_or_a_night_mood_ask_for_night(look: dict[str, Any], night: bool) -> None:
    style = resolve_style(KidsStorySettings.model_validate({"look": look}))
    assert style.night is night and style.hints("a meadow").night is night
