from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from autotube.domain.image_style import Outline, Texture
from autotube.pipelines.kids_story.settings.base import HexColor, SettingsSection
from autotube.pipelines.kids_story.settings.look_choices import (
    BACKGROUND_CHOICES,
    COLOUR_MOOD_CHOICES,
    CUSTOM_STYLE,
    DETAIL_CHOICES,
    LIGHTING_CHOICES,
    OUTLINE_CHOICES,
    PROPORTION_CHOICES,
    STYLE_CHOICES,
    TEXTURE_CHOICES,
)
from autotube.pipelines.kids_story.styles.library import style_ids
from autotube.pipelines.kids_story.styles.modifiers import (
    BackgroundComplexity,
    ColourMood,
    DetailLevel,
    Lighting,
    Proportions,
)

DEFAULT_STYLE = "watercolour_storybook"
DEFAULT_COLOURS = ["#A9D3EE", "#CFE8C0", "#A8D5BA", "#7FB89A", "#F3A69A"]


def colour_list(title: str, description: str) -> Any:
    return Field(
        default_factory=lambda: list(DEFAULT_COLOURS),
        min_length=2,
        max_length=8,
        title=title,
        description=description,
    )


class CustomStyle(SettingsSection):
    prompt: str = Field(
        default="",
        title="Art direction",
        description="Describes the look of every picture, for example "
        "'bright paper collage with soft shadows'.",
    )
    negative_prompt: str = Field(
        default="",
        title="Keep out of this style",
        description="Looks the image model should avoid, added to the safety list in Safety.",
    )
    palette: list[HexColor] = colour_list(
        "Colours", "Main colours of your style, named in the image prompt and painted offline."
    )
    outline: Outline = Field(
        default=Outline.THIN,
        json_schema_extra=OUTLINE_CHOICES,
        title="Outlines",
        description="Outline weight of the offline preview; write outlines into the art direction "
        "for image models.",
    )
    texture: Texture = Field(
        default=Texture.PAPER,
        json_schema_extra=TEXTURE_CHOICES,
        title="Texture",
        description="Surface treatment of the offline preview; write it into the art direction "
        "for image models.",
    )


class LookSettings(SettingsSection):
    visual_style: str = Field(
        default=DEFAULT_STYLE,
        json_schema_extra=STYLE_CHOICES,
        title="Visual style",
        description="The look of every picture: characters, scenes, cards and thumbnails.",
    )
    custom_style: CustomStyle = Field(
        default_factory=CustomStyle,
        title="Custom style",
        description="Used only when the visual style is Custom style.",
    )
    colour_mood: ColourMood = Field(
        default=ColourMood.STYLE,
        json_schema_extra=COLOUR_MOOD_CHOICES,
        title="Colour mood",
        description="Shifts the style's colours; My own colours uses the colours below.",
    )
    mood_palette: list[HexColor] = colour_list(
        "My own colours", "Used only when the colour mood is My own colours."
    )
    lighting: Lighting = Field(
        default=Lighting.STYLE,
        json_schema_extra=LIGHTING_CHOICES,
        title="Lighting",
        description="The light in every picture, added to the image prompt.",
    )
    detail_level: DetailLevel = Field(
        default=DetailLevel.STYLE,
        json_schema_extra=DETAIL_CHOICES,
        title="Detail",
        description="How much small detail the pictures carry, added to the image prompt.",
    )
    background: BackgroundComplexity = Field(
        default=BackgroundComplexity.STYLE,
        json_schema_extra=BACKGROUND_CHOICES,
        title="Background",
        description="How busy the backgrounds are, from a plain backdrop to rich scenery.",
    )
    proportions: Proportions = Field(
        default=Proportions.STYLE,
        json_schema_extra=PROPORTION_CHOICES,
        title="Character proportions",
        description="Body shape of the characters, added to the image prompt.",
    )
    extra_prompt: str = Field(
        default="",
        max_length=400,
        title="Extra art direction",
        description="Added to the end of every picture prompt, whatever the style.",
    )
    extra_negative_prompt: str = Field(
        default="",
        max_length=400,
        title="Extra things to avoid",
        description="Added to the negative prompt of every picture, whatever the style.",
    )
    use_style_motion: bool = Field(
        default=True,
        title="Move the way the style suggests",
        description="Use the style's motion strength, card camera and held frames instead of "
        "the motion settings under Pictures. A custom style always uses those settings.",
    )
    use_style_lettering: bool = Field(
        default=True,
        title="Letter in the style's colours",
        description="Use the style's lettering colours on cards and thumbnails instead of the "
        "title colours under Thumbnail. A custom style always uses those colours.",
    )

    @model_validator(mode="after")
    def check_style(self) -> LookSettings:
        known = (*style_ids(), CUSTOM_STYLE)
        if self.visual_style not in known:
            raise ValueError(f"unknown visual style {self.visual_style}")
        if self.visual_style == CUSTOM_STYLE and not self.custom_style.prompt.strip():
            raise ValueError("a custom style needs its art direction")
        return self
