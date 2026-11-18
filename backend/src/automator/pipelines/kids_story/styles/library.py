from __future__ import annotations

from enum import StrEnum
from functools import cache

from pydantic import Field, TypeAdapter

from automator.domain.capabilities import CameraMove
from automator.domain.image_style import HexColour, Outline, Texture
from automator.domain.model_base import DomainModel
from automator.pipelines.kids_story.resources import resource_json

STYLE_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


class StyleFamily(StrEnum):
    ANIMATED = "animated"
    ILLUSTRATED = "illustrated"
    DRAWN = "drawn"
    CRAFTED = "crafted"
    GRAPHIC = "graphic"
    REALISTIC = "realistic"


FAMILY_TITLES: dict[StyleFamily, str] = {
    StyleFamily.ANIMATED: "Animated",
    StyleFamily.ILLUSTRATED: "Painted and illustrated",
    StyleFamily.DRAWN: "Hand-drawn",
    StyleFamily.CRAFTED: "Crafted",
    StyleFamily.GRAPHIC: "Graphic",
    StyleFamily.REALISTIC: "Realistic",
}


class StyleMotion(DomainModel):
    intensity: float = Field(ge=0, le=1)
    hero_intensity: float = Field(ge=0, le=1)
    card_camera: CameraMove
    held_frame_rate: int | None = Field(default=None, ge=1, le=30)
    feel: str = Field(min_length=1)


class StyleLettering(DomainModel):
    text: HexColour
    outline: HexColour


class StyleBase(DomainModel):
    id: str = Field(pattern=STYLE_ID_PATTERN)
    title: str = Field(min_length=1, max_length=40)
    prompt: str
    negative_prompt: str
    palette: tuple[HexColour, ...]
    outline: Outline
    texture: Texture


class VisualStyle(StyleBase):
    family: StyleFamily
    description: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1)
    palette: tuple[HexColour, ...] = Field(min_length=4, max_length=6)
    motion: StyleMotion
    lettering: StyleLettering


LIBRARY_ADAPTER = TypeAdapter(tuple[VisualStyle, ...])


def parsed_library(raw: object) -> tuple[VisualStyle, ...]:
    styles = LIBRARY_ADAPTER.validate_python(raw)
    ids = [style.id for style in styles]
    repeated = sorted({name for name in ids if ids.count(name) > 1})
    if repeated:
        raise ValueError(f"visual style ids must be unique; repeated: {', '.join(repeated)}")
    return styles


@cache
def style_library() -> tuple[VisualStyle, ...]:
    return parsed_library(resource_json("styles", "library.json"))


def style_ids() -> tuple[str, ...]:
    return tuple(style.id for style in style_library())


def style_named(style_id: str) -> VisualStyle | None:
    return next((style for style in style_library() if style.id == style_id), None)
