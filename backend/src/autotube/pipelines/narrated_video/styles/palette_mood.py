from __future__ import annotations

import colorsys
from collections.abc import Callable, Sequence

from autotube.domain.image_style import rgb_of_hex
from autotube.pipelines.narrated_video.styles.modifiers import ColourMood

Hsv = tuple[float, float, float]
HsvShift = Callable[[Hsv], Hsv]
WARM_HUE = 0.08
COOL_HUE = 0.56
NIGHT_HUE = 0.64


def to_hsv(colour: str) -> Hsv:
    red, green, blue = (channel / 255 for channel in rgb_of_hex(colour))
    return colorsys.rgb_to_hsv(red, green, blue)


def to_hex(hsv: Hsv) -> str:
    channels = colorsys.hsv_to_rgb(hsv[0] % 1.0, clamped(hsv[1]), clamped(hsv[2]))
    return "#" + "".join(f"{round(channel * 255):02X}" for channel in channels)


def clamped(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def toward_hue(hue: float, target: float, share: float) -> float:
    gap = (target - hue + 0.5) % 1.0 - 0.5
    return hue + gap * share


def brighter(hsv: Hsv) -> Hsv:
    return hsv[0], hsv[1] * 1.35 + 0.1, hsv[2] * 1.1 + 0.08


def paler(hsv: Hsv) -> Hsv:
    return hsv[0], hsv[1] * 0.45, 0.82 + hsv[2] * 0.18


def warmer(hsv: Hsv) -> Hsv:
    return toward_hue(hsv[0], WARM_HUE, 0.4), hsv[1] * 1.1 + 0.05, hsv[2]


def cooler(hsv: Hsv) -> Hsv:
    return toward_hue(hsv[0], COOL_HUE, 0.4), hsv[1], hsv[2] * 0.95


def nightly(hsv: Hsv) -> Hsv:
    return toward_hue(hsv[0], NIGHT_HUE, 0.45), hsv[1] * 0.9 + 0.1, hsv[2] * 0.45


def greyed(hsv: Hsv) -> Hsv:
    return hsv[0], 0.0, hsv[2]


MOOD_SHIFTS: dict[ColourMood, HsvShift] = {
    ColourMood.BRIGHT: brighter,
    ColourMood.PASTEL: paler,
    ColourMood.WARM: warmer,
    ColourMood.COOL: cooler,
    ColourMood.NIGHT: nightly,
    ColourMood.MONOCHROME: greyed,
}


def mood_palette(
    palette: Sequence[str], mood: ColourMood, custom: Sequence[str]
) -> tuple[str, ...]:
    if mood is ColourMood.CUSTOM:
        return tuple(colour.upper() for colour in custom)
    shift = MOOD_SHIFTS.get(mood)
    if shift is None:
        return tuple(colour.upper() for colour in palette)
    return tuple(to_hex(shift(to_hsv(colour))) for colour in palette)
