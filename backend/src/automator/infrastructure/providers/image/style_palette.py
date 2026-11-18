from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from automator.domain.image_style import ImageStyleHints, Outline, Texture
from automator.infrastructure.providers.image.scene_palette import Palette, Rgb, palette_for

WHITE: Rgb = (255, 255, 255)
INK_BLACK: Rgb = (20, 20, 24)
NIGHT_SKY: Rgb = (18, 24, 60)
OUTLINE_UNITS: dict[Outline, float] = {Outline.NONE: 0.0, Outline.THIN: 0.35, Outline.BOLD: 0.9}
LIGHT_SKY = 0.5
NIGHT_DARKENING = 0.55


@dataclass(frozen=True)
class Ink:
    color: Rgb
    units: float


def rgb(colour: str) -> Rgb:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def mixed(left: Rgb, right: Rgb, share: float) -> Rgb:
    red, green, blue = (round(a + (b - a) * share) for a, b in zip(left, right, strict=True))
    return red, green, blue


def luminance(color: Rgb) -> float:
    return (0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]) / 255


def land_layers(land: Sequence[Rgb]) -> tuple[Rgb, Rgb, Rgb]:
    picks = [land[round(index * (len(land) - 1) / 2)] for index in range(3)]
    return picks[0], picks[1], picks[2]


def hinted_palette(hints: ImageStyleHints, night: bool) -> Palette:
    colours = [rgb(colour) for colour in hints.palette]
    if night:
        colours = [mixed(colour, NIGHT_SKY, NIGHT_DARKENING) for colour in colours]
    sky, land, accent = colours[0], colours[1:-1] or colours[:1], colours[-1]
    return Palette(
        sky_top=sky,
        sky_bottom=mixed(sky, WHITE, 0.45),
        hills=land_layers(land),
        celestial=mixed(accent, WHITE, 0.55),
        accent=accent,
        night=night,
    )


def ink_for(outline: Outline, palette: Palette) -> Ink | None:
    units = OUTLINE_UNITS[outline]
    if units == 0:
        return None
    colours = [palette.sky_top, *palette.hills, palette.accent]
    if luminance(palette.sky_top) >= LIGHT_SKY:
        return Ink(mixed(min(colours, key=luminance), INK_BLACK, 0.6), units)
    return Ink(mixed(max(colours, key=luminance), WHITE, 0.5), units)


@dataclass(frozen=True)
class SceneStyle:
    palette: Palette
    ink: Ink | None
    texture: Texture

    def swatches(self) -> list[Rgb]:
        palette = self.palette
        inks = [self.ink.color] if self.ink else []
        return [palette.sky_top, palette.sky_bottom, *palette.hills, palette.accent, *inks]


def scene_style(prompt: str, rng: random.Random, hints: ImageStyleHints | None) -> SceneStyle:
    palette = palette_for(prompt, rng)
    if hints is None:
        return SceneStyle(palette, None, Texture.SMOOTH)
    if hints.palette:
        palette = hinted_palette(hints, palette.night)
    return SceneStyle(palette, ink_for(hints.outline, palette), hints.texture)
