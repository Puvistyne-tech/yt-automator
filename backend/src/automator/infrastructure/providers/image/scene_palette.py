from __future__ import annotations

import colorsys
import random
from dataclasses import dataclass

Rgb = tuple[int, int, int]

NIGHT_WORDS = frozenset(
    {"night", "moon", "moonlight", "star", "stars", "sleep", "bedtime", "dream"}
)
DUSK_WORDS = frozenset({"sunset", "sunrise", "evening", "dusk", "dawn", "twilight"})


@dataclass(frozen=True)
class Palette:
    sky_top: Rgb
    sky_bottom: Rgb
    hills: tuple[Rgb, Rgb, Rgb]
    celestial: Rgb
    accent: Rgb
    night: bool


def hsv(hue: float, saturation: float, value: float) -> Rgb:
    red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
    return round(red * 255), round(green * 255), round(blue * 255)


def mood_of(prompt: str) -> str:
    words = {word.strip(".,!?;:'\"").lower() for word in prompt.split()}
    if words & NIGHT_WORDS:
        return "night"
    return "dusk" if words & DUSK_WORDS else "day"


def hill_colors(hue: float, saturation: float, value: float) -> tuple[Rgb, Rgb, Rgb]:
    return (
        hsv(hue - 0.03, saturation * 0.6, value),
        hsv(hue, saturation * 0.8, value * 0.85),
        hsv(hue + 0.03, saturation, value * 0.7),
    )


def palette_for(prompt: str, rng: random.Random) -> Palette:
    base = rng.random()
    accent = hsv(0.85 + base * 0.5, 0.6, 0.98)
    mood = mood_of(prompt)
    if mood == "night":
        sky = (hsv(0.66, 0.7, 0.22), hsv(0.7, 0.45, 0.45))
        hills = hill_colors(0.5 + base * 0.1, 0.5, 0.35)
        return Palette(*sky, hills, hsv(0.14, 0.2, 1.0), accent, night=True)
    if mood == "dusk":
        sky = (hsv(0.75, 0.45, 0.6), hsv(0.07, 0.55, 1.0))
        hills = hill_colors(0.9 + base * 0.15, 0.45, 0.55)
        return Palette(*sky, hills, hsv(0.1, 0.6, 1.0), accent, night=False)
    sky_hue = 0.55 + (base - 0.5) * 0.12
    sky = (hsv(sky_hue, 0.5, 0.95), hsv(sky_hue - 0.04, 0.18, 1.0))
    hills = hill_colors(0.22 + base * 0.14, 0.6, 0.85)
    return Palette(*sky, hills, hsv(0.13, 0.55, 1.0), accent, night=False)
