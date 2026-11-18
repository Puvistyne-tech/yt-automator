from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from autotube.domain.model_base import DomainModel

HEX_COLOUR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
HexColour = Annotated[str, Field(pattern=HEX_COLOUR_PATTERN)]


class Outline(StrEnum):
    NONE = "none"
    THIN = "thin"
    BOLD = "bold"


class Texture(StrEnum):
    SMOOTH = "smooth"
    PAPER = "paper"
    GRAIN = "grain"
    CLAY = "clay"
    PIXEL = "pixel"


class ImageStyleHints(DomainModel):
    palette: tuple[HexColour, ...] = Field(default=(), max_length=12)
    outline: Outline = Outline.NONE
    texture: Texture = Texture.SMOOTH
    night: bool = False
    scene_text: str = ""


def rgb_of_hex(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)
