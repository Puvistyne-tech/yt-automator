from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

from automator.pipelines.kids_story.art.imaging import ImageFailure

SHAPED_LANGUAGES = frozenset({"ta"})
Font = ImageFont.FreeTypeFont


class Placement(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass(frozen=True)
class Lettering:
    lines: tuple[str, ...]
    language: str
    font_files: tuple[str, ...]
    color: str
    outline: str
    size_ratio: float
    margin_ratio: float
    outline_ratio: float
    placement: Placement


@cache
def shaping_available() -> bool:
    return bool(features.check("raqm"))


def can_letter(language: str) -> bool:
    return language not in SHAPED_LANGUAGES or shaping_available()


def load_font(files: Sequence[str], size: int) -> Font | None:
    engine = ImageFont.Layout.RAQM if shaping_available() else ImageFont.Layout.BASIC
    for name in files:
        if Path(name).is_file():
            try:
                return ImageFont.truetype(name, size, layout_engine=engine)
            except OSError:
                continue
    return None


def wrap_to_width(text: str, font: Font, width: float) -> list[str]:
    lines: list[str] = []
    for word in text.split():
        joined = f"{lines[-1]} {word}" if lines else word
        if lines and font.getlength(joined) <= width:
            lines[-1] = joined
        else:
            lines.append(word)
    return lines


def origin(
    placement: Placement, box: tuple[int, int], size: tuple[int, int], margin: int
) -> tuple[int, int]:
    width, height = size
    left = {"left": margin, "right": width - box[0] - margin}
    top = {"top": margin, "bottom": height - box[1] - margin}
    if placement is Placement.CENTER:
        return (width - box[0]) // 2, (height - box[1]) // 2
    vertical, _, horizontal = placement.value.partition("_")
    x = left[horizontal] if horizontal else (width - box[0]) // 2
    return x, top[vertical]


def draw_block(image: Image.Image, lettering: Lettering, font: Font) -> None:
    draw = ImageDraw.Draw(image)
    margin = int(image.height * lettering.margin_ratio)
    wrapped = [
        line
        for text in lettering.lines
        for line in wrap_to_width(text, font, image.width - 2 * margin)
    ]
    block = "\n".join(wrapped)
    stroke = max(1, int(font.size * lettering.outline_ratio))
    left, top, right, bottom = draw.multiline_textbbox(
        (0, 0), block, font=font, stroke_width=stroke
    )
    x, y = origin(lettering.placement, (int(right - left), int(bottom - top)), image.size, margin)
    draw.multiline_text(
        (x - left, y - top),
        block,
        font=font,
        fill=lettering.color,
        stroke_width=stroke,
        stroke_fill=lettering.outline,
        align="center",
    )


def lettered(source: Path, output: Path, lettering: Lettering) -> bool:
    if not can_letter(lettering.language):
        return False
    try:
        with Image.open(source) as opened:
            image = opened.convert("RGB")
        font = load_font(lettering.font_files, max(8, int(image.height * lettering.size_ratio)))
        if font is None:
            return False
        draw_block(image, lettering, font)
        image.save(output, format="PNG")
    except ImageFailure:
        return False
    return True
