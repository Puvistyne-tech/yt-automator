from __future__ import annotations

from collections.abc import Sequence

from pydantic.config import JsonDict

from autotube.domain.image_style import Outline, Texture
from autotube.domain.ui_schema import CHOICE_GROUP_KEY, CHOICE_SWATCHES_KEY
from autotube.pipelines.kids_story.settings.choices import ChoiceSchema, enum_choices
from autotube.pipelines.kids_story.styles.library import FAMILY_TITLES, style_library
from autotube.pipelines.kids_story.styles.modifiers import (
    BackgroundComplexity,
    ColourMood,
    DetailLevel,
    Lighting,
    Proportions,
)

CUSTOM_STYLE = "custom"
CUSTOM_STYLE_ENTRY: JsonDict = {
    "const": CUSTOM_STYLE,
    "title": "Custom style",
    "description": "Write your own art direction, colours, outlines and texture below.",
    CHOICE_GROUP_KEY: "Your own",
}

OUTLINE_CHOICES = enum_choices(
    Outline, {"none": "No outlines", "thin": "Thin outlines", "bold": "Bold outlines"}
)
TEXTURE_CHOICES = enum_choices(
    Texture,
    {"smooth": "Smooth", "paper": "Paper", "grain": "Grain", "clay": "Clay", "pixel": "Pixels"},
)
COLOUR_MOOD_CHOICES = enum_choices(
    ColourMood,
    {
        "style": "Style default",
        "bright": "Bright",
        "pastel": "Pastel",
        "warm": "Warm",
        "cool": "Cool",
        "night": "Night",
        "monochrome": "Monochrome",
        "custom": "My own colours",
    },
)
LIGHTING_CHOICES = enum_choices(
    Lighting,
    {
        "style": "Style default",
        "soft_daylight": "Soft daylight",
        "golden_hour": "Golden hour",
        "moonlight": "Moonlight",
        "studio": "Studio",
        "dramatic": "Dramatic",
    },
)
DETAIL_CHOICES = enum_choices(
    DetailLevel,
    {
        "style": "Style default",
        "minimal": "Minimal",
        "balanced": "Balanced",
        "intricate": "Intricate",
    },
)
BACKGROUND_CHOICES = enum_choices(
    BackgroundComplexity,
    {
        "style": "Style default",
        "plain": "Plain",
        "simple": "Simple",
        "moderate": "Some scenery",
        "rich": "Rich",
    },
)
PROPORTION_CHOICES = enum_choices(
    Proportions, {"style": "Style default", "realistic": "Realistic", "cute": "Cute, big heads"}
)


def card_choices(entries: Sequence[JsonDict]) -> ChoiceSchema:
    def apply(schema: JsonDict) -> None:
        schema.pop("$ref", None)
        schema.pop("enum", None)
        schema["type"] = "string"
        schema["oneOf"] = [dict(entry) for entry in entries]

    return apply


def style_entries() -> list[JsonDict]:
    entries: list[JsonDict] = [
        {
            "const": style.id,
            "title": style.title,
            "description": style.description,
            CHOICE_GROUP_KEY: FAMILY_TITLES[style.family],
            CHOICE_SWATCHES_KEY: list(style.palette),
        }
        for style in style_library()
    ]
    return [*entries, CUSTOM_STYLE_ENTRY]


STYLE_CHOICES = card_choices(style_entries())
