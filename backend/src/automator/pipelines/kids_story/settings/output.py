from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from automator.pipelines.kids_story.settings.base import (
    LocalizedList,
    SettingsSection,
    localized_list,
)
from automator.pipelines.kids_story.settings.subtitles import color

LATIN_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
TAMIL_FONTS = [
    "/System/Library/Fonts/Supplemental/Tamil Sangam MN.ttc",
    "/System/Library/Fonts/Supplemental/Tamil MN.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
]


class LandscapeResolution(StrEnum):
    HD = "1280x720"
    FULL_HD = "1920x1080"
    UHD = "3840x2160"


class PortraitResolution(StrEnum):
    HD = "720x1280"
    FULL_HD = "1080x1920"


class ShortSceneSelection(StrEnum):
    AUTO = "auto"
    FIRST_N = "first_n"


class TextPosition(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"


def size_of(resolution: StrEnum) -> tuple[int, int]:
    width, height = str(resolution.value).split("x")
    return int(width), int(height)


class EpisodeSettings(SettingsSection):
    resolution: LandscapeResolution = Field(
        default=LandscapeResolution.FULL_HD, title="Resolution", description="Episode size."
    )
    fps: int = Field(default=30, ge=12, le=60, title="Frames per second", description="Episode.")
    intro_card: bool = Field(default=True, title="Intro card", description="Open with a card.")
    outro_card: bool = Field(default=True, title="Outro card", description="Close with a card.")
    card_seconds: float = Field(
        default=3.0, gt=0, le=15, title="Card length", description="Shortest card, in seconds."
    )
    scene_lead_in_seconds: float = Field(
        default=0.4, ge=0, le=5, title="Pause before narration", description="Per scene."
    )
    scene_tail_seconds: float = Field(
        default=0.8, ge=0, le=5, title="Pause after narration", description="Per scene."
    )
    min_scene_seconds: float = Field(
        default=3.0, gt=0, le=30, title="Shortest scene", description="Seconds."
    )
    loudness_lufs: float = Field(
        default=-16.0, ge=-30, le=-8, title="Loudness target", description="Integrated LUFS."
    )
    fade_seconds: float = Field(
        default=0.5, ge=0, le=5, title="Fade", description="Fade in and out, in seconds."
    )


class ShortSettings(SettingsSection):
    enabled: bool = Field(default=True, title="Make a Short", description="Vertical 9:16 cut.")
    resolution: PortraitResolution = Field(
        default=PortraitResolution.FULL_HD, title="Resolution", description="Short size."
    )
    max_duration_seconds: float = Field(
        default=58, ge=10, le=60, title="Longest Short", description="Seconds."
    )
    scene_selection: ShortSceneSelection = Field(
        default=ShortSceneSelection.AUTO,
        title="Scenes",
        description="Let the story pick the best scenes, or use the first scenes.",
    )
    first_n_scenes: int = Field(
        default=4, ge=1, le=10, title="First scenes", description="Used with first scenes."
    )
    max_scenes: int = Field(
        default=5, ge=1, le=10, title="Most scenes", description="Scenes the Short may use."
    )
    hook_line: bool = Field(
        default=True, title="Hook line", description="Open the Short with the story's hook line."
    )


class ThumbnailSettings(SettingsSection):
    title_text: bool = Field(
        default=True, title="Title on thumbnail", description="Draw the story title."
    )
    width: int = Field(default=1280, ge=320, le=3840, title="Width", description="Pixels.")
    height: int = Field(default=720, ge=180, le=2160, title="Height", description="Pixels.")
    text_position: TextPosition = Field(
        default=TextPosition.BOTTOM, title="Title position", description="Top or bottom."
    )
    text_size_ratio: float = Field(
        default=0.11,
        gt=0,
        le=0.4,
        title="Title size",
        description="Letter height as a share of the thumbnail height.",
    )
    margin_ratio: float = Field(
        default=0.05,
        ge=0,
        le=0.3,
        title="Title margin",
        description="Space between the title and the edge, as a share of the height.",
    )
    outline_ratio: float = Field(
        default=0.08,
        ge=0,
        le=0.5,
        title="Outline thickness",
        description="Outline width as a share of the letter height.",
    )
    text_color: str = color("#FFFFFF", "Title colour", "Colour of the title letters.")
    outline_color: str = color("#3A2A1A", "Title outline", "Colour around the title letters.")
    font_files: LocalizedList = localized_list(
        LATIN_FONTS, TAMIL_FONTS, "Font files", "Font files tried in order, per language."
    )
