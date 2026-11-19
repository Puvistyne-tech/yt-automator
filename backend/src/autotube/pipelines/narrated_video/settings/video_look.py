from __future__ import annotations

from typing import Any

from pydantic import Field, ValidationInfo, field_validator

from autotube.domain.video_look import Transition, VideoQuality
from autotube.pipelines.narrated_video.settings.base import (
    LocalizedText,
    Placement,
    SettingsSection,
    localized_text,
)
from autotube.pipelines.narrated_video.settings.choices import (
    PLACEMENT_CHOICES,
    TRANSITION_CHOICES,
    VIDEO_QUALITY_CHOICES,
)
from autotube.pipelines.narrated_video.settings.placeholders import (
    CARD_PLACEHOLDERS,
    checked_template,
)

FOLLOW_EPISODE_FPS = 0
LOWEST_FPS = 12
CARD_NOTE = (
    "One line per row; {title} {series} {tagline} {moral} {hook} and {refrain} are filled in."
)


def video_quality_field(video: str) -> Any:
    return Field(
        default=VideoQuality.STANDARD,
        json_schema_extra=VIDEO_QUALITY_CHOICES,
        title="Video quality",
        description=f"Picture quality of the {video} against file size. Standard keeps the "
        "media provider's quality setting.",
    )


class EpisodeLookSettings(SettingsSection):
    intro_card_text: LocalizedText = localized_text(
        "{series}\n{title}", "{series}\n{title}", "Intro card text", CARD_NOTE
    )
    outro_card_text: LocalizedText = localized_text(
        "{refrain}\n{series}", "{refrain}\n{series}", "Outro card text", CARD_NOTE
    )
    card_text_position: Placement = Field(
        default=Placement.CENTER,
        json_schema_extra=PLACEMENT_CHOICES,
        title="Card text position",
        description="Where the text sits on the intro and outro cards.",
    )
    transition: Transition = Field(
        default=Transition.CUT,
        json_schema_extra=TRANSITION_CHOICES,
        title="Transition",
        description="How one picture gives way to the next in the episode and the Short. "
        "A crossfade or fade overlaps the pictures, so the video gets a little shorter.",
    )
    transition_seconds: float = Field(
        default=0.5,
        gt=0,
        le=3,
        title="Transition length",
        description="Seconds each crossfade or fade lasts; shortened where a scene is too short "
        "or the narration would overlap. A cut ignores it.",
    )
    video_quality: VideoQuality = video_quality_field("episode")

    @field_validator("intro_card_text", "outro_card_text")
    @classmethod
    def check_card_text(cls, value: LocalizedText, info: ValidationInfo) -> LocalizedText:
        return checked_template(f"episode.{info.field_name}", value, CARD_PLACEHOLDERS)

    def overlap_seconds(self) -> float:
        return 0.0 if self.transition is Transition.CUT else self.transition_seconds


class ShortLookSettings(SettingsSection):
    fps: int = Field(
        default=FOLLOW_EPISODE_FPS,
        ge=FOLLOW_EPISODE_FPS,
        le=60,
        title="Frames per second",
        description="Frames per second of the Short, from 12 to 60; 0 follows the episode.",
    )
    video_quality: VideoQuality = video_quality_field("Short")

    @field_validator("fps")
    @classmethod
    def check_fps(cls, value: int) -> int:
        if value != FOLLOW_EPISODE_FPS and value < LOWEST_FPS:
            raise ValueError(f"short.fps must be 0 or from {LOWEST_FPS} to 60")
        return value
