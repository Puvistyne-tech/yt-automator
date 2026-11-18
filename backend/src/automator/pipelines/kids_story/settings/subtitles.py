from __future__ import annotations

from pydantic import Field

from automator.pipelines.kids_story.settings.base import (
    HEX_COLOR,
    LocalizedText,
    SettingsSection,
    localized_text,
)


def color(default: str, title: str, description: str) -> str:
    field: str = Field(
        default=default,
        pattern=HEX_COLOR,
        title=title,
        description=description,
        json_schema_extra={"format": "color"},
    )
    return field


class SubtitleSettings(SettingsSection):
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
        description="Most lines of text shown on screen at the same time.",
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
        description="Fewest seconds one subtitle stays on screen, so children can read it.",
    )
    font_family: LocalizedText = localized_text(
        "Noto Sans",
        "Noto Sans Tamil",
        "Font",
        "Name of the font burned-in subtitles are drawn with, per language.",
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
    primary_color: str = color("#FFFFFF", "Text colour", "Colour of the letters.")
    outline_color: str = color("#000000", "Outline colour", "Colour around the letters.")
    highlight_color: str = color("#FFD54A", "Highlight colour", "Colour of the spoken word.")
    margin_bottom: int = Field(
        default=90,
        ge=0,
        le=1000,
        title="Bottom margin",
        description="Pixels between burned-in subtitles and the bottom of the episode.",
    )
    short_margin_bottom: int = Field(
        default=320,
        ge=0,
        le=1500,
        title="Bottom margin in Shorts",
        description="Pixels between burned-in subtitles and the bottom of the Short.",
    )

    @property
    def captions_uploaded(self) -> bool:
        return self.enabled and self.upload_captions
