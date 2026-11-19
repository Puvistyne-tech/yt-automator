from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from autotube.domain.image_style import HEX_COLOUR_PATTERN
from autotube.domain.model_base import DomainModel

SMALLEST_SUBTITLE_FONT_SIZE = 8


class SubtitlePosition(StrEnum):
    BOTTOM = "bottom"
    MIDDLE = "middle"
    TOP = "top"


class Transition(StrEnum):
    CUT = "cut"
    CROSSFADE = "crossfade"
    FADE_THROUGH_BLACK = "fade_through_black"


class VideoQuality(StrEnum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    BEST = "best"


class ScreenCorner(StrEnum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class SubtitleStyle(DomainModel):
    burn_in: bool = False
    font_family: str = "Noto Sans"
    font_size: int = Field(default=54, ge=SMALLEST_SUBTITLE_FONT_SIZE)
    primary_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    highlight_color: str = "#FFD54A"
    margin_bottom: int = Field(default=90, ge=0)
    margin_sides: int = Field(default=40, ge=0)
    font_file: Path | None = None
    wrap_lines: bool = False
    karaoke: bool = False
    position: SubtitlePosition = SubtitlePosition.BOTTOM
    bold: bool = False
    shadow: float = Field(default=0.0, ge=0.0)
    box: bool = False
    box_color: str = Field(default="#000000", pattern=HEX_COLOUR_PATTERN)
    box_opacity: float = Field(default=0.6, ge=0.0, le=1.0)
    outline_width: float | None = Field(default=None, ge=0.0)


class Watermark(DomainModel):
    image: Path
    corner: ScreenCorner = ScreenCorner.TOP_RIGHT
    width_share: float = Field(default=0.12, gt=0.0, le=1.0)
    opacity: float = Field(default=0.8, ge=0.0, le=1.0)
    margin_share: float = Field(default=0.03, ge=0.0, le=0.5)
