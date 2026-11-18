from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from automator.domain.capabilities import CameraMove
from automator.domain.image_style import Outline, Texture
from automator.pipelines.kids_story.settings.legacy_look import (
    LEGACY_ART_STYLE,
    LEGACY_NEGATIVE_PROMPT,
)
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.styles.colour_names import colour_name, colour_words
from automator.pipelines.kids_story.styles.library import style_named
from automator.pipelines.kids_story.styles.modifiers import (
    BACKGROUND_PROMPTS,
    DETAIL_PROMPTS,
    LIGHTING_PROMPTS,
    MOOD_PROMPTS,
    PROPORTION_PROMPTS,
    STYLE_DEFAULT,
    ColourMood,
)
from automator.pipelines.kids_story.styles.palette_mood import mood_palette, to_hsv
from automator.pipelines.kids_story.styles.resolve import (
    ResolvedStyle,
    joined_terms,
    resolve_style,
)

CUSTOM: dict[str, Any] = {
    "visual_style": "custom",
    "custom_style": {
        "prompt": "bright paper collage",
        "negative_prompt": "photo",
        "palette": ["#FF0000", "#00FF00", "#0000FF"],
        "outline": "bold",
        "texture": "pixel",
    },
}


def resolved(**look: Any) -> ResolvedStyle:
    return resolve_style(KidsStorySettings.model_validate({"look": look}))


def test_the_default_look_keeps_the_previous_watercolour_prompts() -> None:
    style = resolve_style(KidsStorySettings())
    assert style.style_id == "watercolour_storybook"
    assert style.prompt == LEGACY_ART_STYLE
    legacy_terms = {term.strip() for term in LEGACY_NEGATIVE_PROMPT.split(",")}
    assert {term.strip() for term in style.negative_prompt.split(",")} == legacy_terms
    assert (style.lettering.text, style.lettering.outline) == ("#FFFFFF", "#3A2A1A")
    assert (style.motion.intensity, style.motion.hero_intensity) == (0.5, 0.7)


def test_a_library_style_supplies_prompt_hints_motion_and_lettering() -> None:
    style = resolved(visual_style="claymation")
    entry = style_named("claymation")
    assert entry is not None
    assert style.prompt == entry.prompt and style.palette == entry.palette
    assert (style.outline, style.texture) == (Outline.NONE, Texture.CLAY)
    assert style.motion.held_frame_rate == 12 and style.motion.card_camera is CameraMove.STILL
    assert style.lettering == entry.lettering
    assert style.hints().texture is Texture.CLAY


def test_the_safety_list_and_extra_negatives_join_every_negative_prompt() -> None:
    style = resolved(visual_style="realistic_photo", extra_negative_prompt="umbrellas, Cartoon")
    assert style.negative_prompt.startswith("text, letters")
    assert "violence" in style.negative_prompt and "cartoon" in style.negative_prompt
    assert style.negative_prompt.endswith("umbrellas")


def test_joined_terms_drop_repeats_and_blanks() -> None:
    assert joined_terms(["a, b", " B ,, c", ""]) == "a, b, c"


@pytest.mark.parametrize(
    ("field", "value", "fragment"),
    [
        ("lighting", "golden_hour", LIGHTING_PROMPTS),
        ("detail_level", "minimal", DETAIL_PROMPTS),
        ("background", "rich", BACKGROUND_PROMPTS),
        ("proportions", "cute", PROPORTION_PROMPTS),
        ("colour_mood", "pastel", MOOD_PROMPTS),
    ],
)
def test_each_modifier_adds_its_wording(field: str, value: str, fragment: dict[Any, str]) -> None:
    style = resolved(**{field: value})
    wording = next(text for key, text in fragment.items() if key.value == value)
    assert style.prompt == f"{LEGACY_ART_STYLE}, {wording}"


def test_style_default_modifiers_add_nothing() -> None:
    defaults = {"lighting", "detail_level", "background", "proportions", "colour_mood"}
    assert resolved(**dict.fromkeys(defaults, STYLE_DEFAULT)).prompt == LEGACY_ART_STYLE


def test_extra_art_direction_goes_last() -> None:
    assert resolved(extra_prompt="  tiny hats ").prompt.endswith(", tiny hats")


@pytest.mark.parametrize("mood", ["bright", "pastel", "warm", "cool", "night", "monochrome"])
def test_every_colour_mood_shifts_the_palette(mood: str) -> None:
    base = resolved().palette
    assert resolved(colour_mood=mood).palette != base


def test_moods_move_colours_the_expected_way() -> None:
    base = resolved().palette
    assert all(to_hsv(c)[1] == 0 for c in resolved(colour_mood="monochrome").palette)
    night = resolved(colour_mood="night").palette
    assert sum(to_hsv(c)[2] for c in night) < sum(to_hsv(c)[2] for c in base)
    assert mood_palette(["#336699"], ColourMood.STYLE, []) == ("#336699",)


def test_my_own_colours_replace_the_palette_and_are_named_in_the_prompt() -> None:
    style = resolved(colour_mood="custom", mood_palette=["#ff0000", "#0000ff"])
    assert style.palette == ("#FF0000", "#0000FF")
    assert style.prompt.endswith("colour palette built from these colours: red, blue")


def test_colour_names_pick_the_nearest_and_skip_repeats() -> None:
    assert colour_name("#FAFAF0") == "white"
    assert colour_words(["#D22828", "#D02A2A", "#285AC8"]) == "red, blue"


def test_a_custom_style_uses_its_own_fields_and_the_settings_motion() -> None:
    settings = KidsStorySettings.model_validate(
        {
            "look": CUSTOM,
            "visuals": {"motion_intensity": 0.1},
            "thumbnail": {"text_color": "#123456"},
        }
    )
    style = resolve_style(settings)
    assert style.style_id == "custom" and style.title == "Custom style"
    assert style.prompt == "bright paper collage, main colours red, green, blue"
    assert style.negative_prompt.endswith("photo")
    assert (style.outline, style.texture) == (Outline.BOLD, Texture.PIXEL)
    assert style.motion.intensity == 0.1 and style.motion.feel == ""
    assert style.lettering.text == "#123456"


def test_turning_off_style_motion_and_lettering_uses_the_settings() -> None:
    settings = KidsStorySettings.model_validate(
        {
            "look": {"visual_style": "comic_book", "use_style_motion": False},
            "visuals": {"hero_motion_intensity": 0.2, "card_camera": "rise"},
        }
    )
    style = resolve_style(settings)
    assert (style.motion.hero_intensity, style.motion.card_camera) == (0.2, CameraMove.RISE)
    assert style.lettering.text == "#FFD60A"
    off = settings.model_copy(
        update={"look": settings.look.model_copy(update={"use_style_lettering": False})}
    )
    assert resolve_style(off).lettering.text == "#FFFFFF"


@pytest.mark.parametrize(
    ("look", "message"),
    [
        ({"visual_style": "mystery"}, "unknown visual style mystery"),
        ({"visual_style": "custom"}, "a custom style needs its art direction"),
        ({"visual_style": "custom", "custom_style": {"prompt": "   "}}, "needs its art direction"),
        ({"mood_palette": ["#FFFFFF"]}, "at least 2"),
    ],
)
def test_an_invalid_look_is_refused(look: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        KidsStorySettings.model_validate({"look": look})
