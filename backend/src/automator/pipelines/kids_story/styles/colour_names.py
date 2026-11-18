from __future__ import annotations

from collections.abc import Sequence

from automator.domain.image_style import rgb_of_hex

NAMED_COLOURS: dict[str, tuple[int, int, int]] = {
    "black": (20, 20, 20),
    "charcoal grey": (70, 70, 75),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "white": (250, 250, 250),
    "cream": (250, 240, 215),
    "beige": (215, 195, 160),
    "brown": (120, 75, 40),
    "red": (210, 40, 40),
    "coral": (245, 125, 110),
    "pink": (245, 170, 195),
    "peach": (250, 205, 165),
    "orange": (245, 140, 30),
    "gold": (225, 180, 60),
    "yellow": (250, 220, 60),
    "olive green": (130, 140, 60),
    "green": (60, 170, 80),
    "mint": (170, 225, 190),
    "teal": (30, 140, 140),
    "sky blue": (140, 200, 240),
    "blue": (40, 90, 200),
    "navy": (25, 40, 90),
    "lavender": (200, 180, 235),
    "purple": (120, 60, 160),
}


def distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> int:
    return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))


def colour_name(colour: str) -> str:
    rgb = rgb_of_hex(colour)
    return min(NAMED_COLOURS, key=lambda name: distance(NAMED_COLOURS[name], rgb))


def colour_words(colours: Sequence[str]) -> str:
    names = list(dict.fromkeys(colour_name(colour) for colour in colours))
    return ", ".join(names)
