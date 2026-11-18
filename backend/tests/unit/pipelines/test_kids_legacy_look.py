from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.kids_story.settings.legacy_look import (
    LEGACY_ART_STYLE,
    LEGACY_NEGATIVE_PROMPT,
    migrated_look,
)
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.styles.resolve import resolve_style


def old_series(**values: object) -> dict[str, Any]:
    return {"series": {"name": {"en": "Tales", "ta": "கதை"}, **values}}


def test_old_default_art_style_migrates_to_watercolour_keeping_motion_and_lettering() -> None:
    settings = KidsStorySettings.model_validate(
        old_series(art_style=LEGACY_ART_STYLE, negative_prompt=LEGACY_NEGATIVE_PROMPT)
    )
    assert settings.look.visual_style == "watercolour_storybook"
    assert not settings.look.use_style_motion and not settings.look.use_style_lettering
    assert settings.series.name.en == "Tales"
    assert resolve_style(settings).prompt == LEGACY_ART_STYLE


@pytest.mark.parametrize(
    "stored",
    [
        {"art_style": LEGACY_ART_STYLE},
        {"negative_prompt": LEGACY_NEGATIVE_PROMPT},
        {"art_style": ""},
        {"art_style": "   "},
        {"art_style": None},
        {"art_style": 7, "negative_prompt": LEGACY_NEGATIVE_PROMPT},
        {"art_style": "  ", "negative_prompt": None},
    ],
)
def test_default_blank_or_unusable_old_values_fall_back_to_watercolour(
    stored: dict[str, object],
) -> None:
    settings = KidsStorySettings.model_validate(old_series(**stored))
    assert settings.look.visual_style == "watercolour_storybook"
    assert resolve_style(settings).prompt == LEGACY_ART_STYLE


def test_an_old_art_style_of_any_length_still_loads() -> None:
    long_style = "soft crayon hills, " * 200
    negative = "rain, " * 400
    settings = KidsStorySettings.model_validate(
        old_series(art_style=long_style, negative_prompt=negative)
    )
    assert settings.look.custom_style.prompt == long_style
    assert settings.look.custom_style.negative_prompt == negative


def test_an_old_custom_art_style_keeps_its_look_as_a_custom_style() -> None:
    settings = KidsStorySettings.model_validate(old_series(art_style="bold crayon scribbles"))
    style = resolve_style(settings)
    assert settings.look.visual_style == "custom"
    assert style.prompt.startswith("bold crayon scribbles")
    assert "realistic photo" in style.negative_prompt


def test_an_old_custom_negative_prompt_alone_is_kept_too() -> None:
    settings = KidsStorySettings.model_validate(old_series(negative_prompt="rain, puddles"))
    assert settings.look.custom_style.prompt == LEGACY_ART_STYLE
    assert resolve_style(settings).negative_prompt.endswith("rain, puddles")


def test_an_existing_look_wins_over_old_series_keys() -> None:
    data = {
        **old_series(art_style="crayons", negative_prompt="x"),
        "look": {"visual_style": "anime"},
    }
    migrated = migrated_look(data)
    assert isinstance(migrated, dict)
    assert set(migrated["series"]) == {"name"}
    assert KidsStorySettings.model_validate(data).look.visual_style == "anime"


@pytest.mark.parametrize("data", [None, [], {"series": "x"}, {"series": {"name": {}}}, {}])
def test_settings_without_old_keys_pass_through_unchanged(data: object) -> None:
    assert migrated_look(data) == data
