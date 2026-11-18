from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from autotube.pipelines.kids_story.settings.choices import (
    LANDSCAPE_CHOICES,
    PORTRAIT_CHOICES,
    SCENE_SELECTION_CHOICES,
)
from autotube.pipelines.kids_story.settings.video_look import EpisodeLookSettings, ShortLookSettings


class LandscapeResolution(StrEnum):
    PREVIEW = "640x360"
    HD = "1280x720"
    FULL_HD = "1920x1080"
    UHD = "3840x2160"


class PortraitResolution(StrEnum):
    PREVIEW = "360x640"
    HD = "720x1280"
    FULL_HD = "1080x1920"


class ShortSceneSelection(StrEnum):
    AUTO = "auto"
    FIRST_N = "first_n"


def size_of(resolution: StrEnum) -> tuple[int, int]:
    width, height = str(resolution.value).split("x")
    return int(width), int(height)


class EpisodeSettings(EpisodeLookSettings):
    resolution: LandscapeResolution = Field(
        default=LandscapeResolution.FULL_HD,
        json_schema_extra=LANDSCAPE_CHOICES,
        title="Resolution",
        description="Width and height of the 16:9 episode video.",
    )
    fps: int = Field(
        default=30,
        ge=12,
        le=60,
        title="Frames per second",
        description="Frames per second of the episode, and of the Short unless it sets its own.",
    )
    intro_card: bool = Field(
        default=True,
        title="Intro card",
        description="Open the episode with a card showing the intro card text.",
    )
    outro_card: bool = Field(
        default=True,
        title="Outro card",
        description="Close the episode with a card showing the outro card text.",
    )
    card_seconds: float = Field(
        default=3.0,
        gt=0,
        le=15,
        title="Card length",
        description="Shortest time in seconds an intro or outro card stays on screen.",
    )
    card_text_size_ratio: float = Field(
        default=0.11,
        gt=0,
        le=0.4,
        title="Card text size",
        description="Letter height on the intro and outro cards as a share of the card height.",
    )
    scene_lead_in_seconds: float = Field(
        default=0.4,
        ge=0,
        le=5,
        title="Pause before narration",
        description="Seconds of picture shown in each scene before the narrator starts.",
    )
    scene_tail_seconds: float = Field(
        default=0.8,
        ge=0,
        le=5,
        title="Pause after narration",
        description="Seconds each scene stays on screen after the narrator finishes.",
    )
    min_scene_seconds: float = Field(
        default=3.0,
        gt=0,
        le=30,
        title="Shortest scene",
        description="Shortest time in seconds any scene stays on screen.",
    )
    loudness_lufs: float = Field(
        default=-16.0,
        ge=-30,
        le=-8,
        title="Loudness target",
        description="Overall loudness every video is mixed to, in integrated LUFS.",
    )
    fade_seconds: float = Field(
        default=0.5,
        ge=0,
        le=5,
        title="Fade",
        description="Seconds of fade in at the start and fade out at the end of every video.",
    )


class ShortSettings(ShortLookSettings):
    enabled: bool = Field(
        default=True,
        title="Make a Short",
        description="Also make a vertical 9:16 Short from the best scenes of each story.",
    )
    resolution: PortraitResolution = Field(
        default=PortraitResolution.FULL_HD,
        json_schema_extra=PORTRAIT_CHOICES,
        title="Resolution",
        description="Width and height of the vertical Short video.",
    )
    max_duration_seconds: float = Field(
        default=58,
        ge=10,
        le=60,
        title="Longest Short",
        description="Most seconds a Short may last; scenes that do not fit are left out.",
    )
    scene_selection: ShortSceneSelection = Field(
        default=ShortSceneSelection.AUTO,
        json_schema_extra=SCENE_SELECTION_CHOICES,
        title="Scenes",
        description="Let the story pick the best scenes, or use the first scenes.",
    )
    first_n_scenes: int = Field(
        default=4,
        ge=1,
        le=10,
        title="First scenes",
        description="How many opening scenes the Short uses when scenes are taken from the start.",
    )
    max_scenes: int = Field(
        default=5,
        ge=1,
        le=10,
        title="Most scenes",
        description="Most scenes a Short may use, whichever way they are chosen.",
    )
    hook_line: bool = Field(
        default=True, title="Hook line", description="Open the Short with the story's hook line."
    )
    hook_style: str = Field(
        default="gentle, curious",
        min_length=1,
        max_length=200,
        title="Hook style",
        description="How the hook line sounds: 'one <hook style> sentence that opens the Short'.",
    )
