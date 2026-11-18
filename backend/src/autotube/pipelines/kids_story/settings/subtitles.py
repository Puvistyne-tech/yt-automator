from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from autotube.domain.font_names import safe_font_family
from autotube.pipelines.kids_story.settings.base import (
    HexColor,
    LocalizedList,
    LocalizedNumber,
    LocalizedText,
    color,
    localized_list,
    localized_number,
    localized_text,
)
from autotube.pipelines.kids_story.settings.subtitle_look import SubtitleLookSettings

LATIN_SUBTITLE_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
RETIRED_KEYS = ("margin_bottom", "short_margin_bottom")
TAMIL_SUBTITLE_FONTS = [
    "/System/Library/Fonts/Supplemental/Tamil Sangam MN.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
]


class SubtitleSettings(SubtitleLookSettings):
    enabled: bool = Field(
        default=True,
        title="Subtitles",
        description="Make subtitles from the narration's word timings.",
    )
    upload_captions: bool = Field(
        default=True,
        title="Upload caption tracks",
        description="Publish the subtitles as YouTube caption tracks.",
    )
    burn_in_episode: bool = Field(
        default=False,
        title="Burn into the episode",
        description="Draw subtitles into the 16:9 episode picture.",
    )
    burn_in_short: bool = Field(
        default=True,
        title="Burn into the Short",
        description="Draw subtitles into the vertical Short picture.",
    )
    max_chars_per_line: int = Field(
        default=42,
        ge=10,
        le=80,
        title="Letters per line",
        description="Most letters on one subtitle line in the episode.",
    )
    short_max_chars_per_line: int = Field(
        default=26,
        ge=8,
        le=60,
        title="Letters per line in Shorts",
        description="Most letters on one subtitle line in the Short.",
    )
    max_lines: int = Field(
        default=2,
        ge=1,
        le=3,
        title="Lines per cue",
        description="Most lines of text shown on screen at the same time in the episode. Text "
        "is never dropped: a word too long to show in parts may exceed this.",
    )
    short_max_lines: int = Field(
        default=2,
        ge=1,
        le=3,
        title="Lines per cue in Shorts",
        description="Most lines of text shown on screen at the same time in the Short. Text "
        "is never dropped: a word too long to show in parts may exceed this.",
    )
    max_cue_seconds: float = Field(
        default=6.0,
        gt=0,
        le=20,
        title="Longest cue",
        description="Most seconds one subtitle may stay on screen.",
    )
    min_cue_seconds: float = Field(
        default=0.7,
        ge=0,
        le=5,
        title="Shortest cue",
        description="Fewest seconds one subtitle stays on screen, so children can read it. "
        "When a cue is split and there is not enough time, the parts join into one screen.",
    )
    font_files: LocalizedList = localized_list(
        LATIN_SUBTITLE_FONTS,
        TAMIL_SUBTITLE_FONTS,
        "Font files",
        "Font files tried in order for burned-in subtitles; the first one that loads draws every "
        "line and measures it where the script can be shaped. Its own font name is used.",
        machine_local=True,
    )
    font_family: LocalizedText = localized_text(
        "Noto Sans",
        "Noto Sans Tamil",
        "Fallback font",
        "Font name used, with the letter width estimate, when no font file loads or its name has "
        "characters other than letters, digits, spaces, '-' and '_'.",
    )
    letter_width_estimate: LocalizedNumber = localized_number(
        0.6,
        1.15,
        "Letter width estimate",
        "Width of one letter as a share of the font size, used to wrap lines when no font file "
        "is found. Higher is safer.",
    )
    font_size: int = Field(
        default=54,
        ge=8,
        le=200,
        title="Font size",
        description="Size of burned-in subtitle letters in the episode, in pixels.",
    )
    short_font_size: int = Field(
        default=64,
        ge=8,
        le=200,
        title="Font size in Shorts",
        description="Size of burned-in subtitle letters in the Short, in pixels.",
    )
    primary_color: HexColor = color("#FFFFFF", "Text colour", "Colour of the letters.")
    outline_color: HexColor = color("#000000", "Outline colour", "Colour around the letters.")
    highlight_color: HexColor = color(
        "#FFD54A", "Highlight colour", "Colour of the spoken word when the karaoke highlight is on."
    )
    bottom_margin_share: float = Field(
        default=0.08,
        ge=0,
        le=0.6,
        title="Bottom margin",
        description="Space below burned-in subtitles in the episode, as a share of its height.",
    )
    short_bottom_margin_share: float = Field(
        default=0.22,
        ge=0,
        le=0.6,
        title="Bottom margin in Shorts",
        description="Space below burned-in subtitles in the Short, as a share of its height. "
        "The default keeps them in the lower third, above the Shorts title and buttons.",
    )
    side_margin_share: float = Field(
        default=0.04,
        ge=0,
        le=0.3,
        title="Side margins",
        description="Space kept clear at the left and right of every subtitle line, as a share "
        "of the picture width.",
    )

    @field_validator("font_family")
    @classmethod
    def check_font_family(cls, value: LocalizedText) -> LocalizedText:
        unsafe = [name for name in (value.en, value.ta) if not safe_font_family(name)]
        if unsafe:
            raise ValueError("font names may only use letters, digits, spaces, '-' and '_'")
        return value

    @model_validator(mode="before")
    @classmethod
    def drop_retired_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return {key: value for key, value in data.items() if key not in RETIRED_KEYS}

    @property
    def captions_uploaded(self) -> bool:
        return self.enabled and self.upload_captions
