from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TypedDict

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from automator.domain.image_style import ImageStyleHints
from automator.infrastructure.providers.image.scene_palette import Palette, Rgb
from automator.infrastructure.providers.image.style_palette import Ink, SceneStyle, scene_style
from automator.infrastructure.providers.image.style_texture import textured

Point = tuple[float, float]
Box = tuple[float, float, float, float]
TRUNK: Rgb = (110, 78, 52)


class Stroke(TypedDict):
    outline: Rgb | None
    width: int


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    ink: Ink | None = None

    @property
    def unit(self) -> float:
        return min(self.width, self.height) / 100

    @property
    def stroke(self) -> int:
        return 0 if self.ink is None else max(1, round(self.ink.units * self.unit))

    def inked(self) -> Stroke:
        return Stroke(outline=None if self.ink is None else self.ink.color, width=self.stroke)


def gradient(canvas: Canvas, top: Rgb, bottom: Rgb) -> Image.Image:
    ramp = np.linspace(0.0, 1.0, canvas.height)[:, None, None]
    colors = np.array(top)[None, None, :] * (1 - ramp) + np.array(bottom)[None, None, :] * ramp
    rows = np.repeat(colors, canvas.width, axis=1).astype(np.uint8)
    return Image.fromarray(rows).convert("RGBA")


def circle(center: Point, radius: float) -> Box:
    return center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius


def glow(image: Image.Image, canvas: Canvas, center: Point, radius: float, color: Rgb) -> None:
    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pen = ImageDraw.Draw(halo)
    for step in range(4, 0, -1):
        pen.ellipse(circle(center, radius * (1 + step * 0.45)), fill=(*color, 28))
    image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(radius * 0.6)))
    ImageDraw.Draw(image).ellipse(circle(center, radius), fill=(*color, 255), **canvas.inked())


def sky_details(image: Image.Image, canvas: Canvas, palette: Palette, rng: random.Random) -> None:
    pen = ImageDraw.Draw(image)
    if palette.night:
        for _ in range(int(canvas.width * canvas.height / (canvas.unit**2 * 120)) + 20):
            x, y = rng.uniform(0, canvas.width), rng.uniform(0, canvas.height * 0.55)
            pen.ellipse(
                circle((x, y), rng.uniform(0.15, 0.45) * canvas.unit), fill=(255, 250, 220, 230)
            )
        return
    for _ in range(rng.randint(2, 4)):
        cloud(pen, canvas, rng)


def puff_boxes(canvas: Canvas, rng: random.Random) -> list[Box]:
    x, y = rng.uniform(0, canvas.width), rng.uniform(0.08, 0.32) * canvas.height
    size = rng.uniform(5, 9) * canvas.unit
    boxes = []
    for offset in (-1.1, -0.4, 0.4, 1.1):
        lift = size * (0.55 if abs(offset) < 1 else 0.25)
        left, top = x + offset * size - size * 0.7, y - lift - size * 0.5
        boxes.append((left, top, left + size * 1.4, y + size * 0.45))
    return boxes


def grown(box: Box, by: float) -> Box:
    return box[0] - by, box[1] - by, box[2] + by, box[3] + by


def cloud(pen: ImageDraw.ImageDraw, canvas: Canvas, rng: random.Random) -> None:
    boxes = puff_boxes(canvas, rng)
    if canvas.ink is not None:
        for box in boxes:
            pen.ellipse(grown(box, canvas.stroke), fill=(*canvas.ink.color, 255))
    for box in boxes:
        pen.ellipse(box, fill=(255, 255, 255, 215 if canvas.ink is None else 255))


def hill_curve(
    canvas: Canvas, rng: random.Random, baseline: float, amplitude: float
) -> list[Point]:
    waves = [(rng.uniform(0.6, 2.2), rng.uniform(0, math.tau), rng.uniform(0.4, 1.0)) for _ in "ab"]
    points = []
    for column in range(0, canvas.width + 8, 8):
        phase = column / canvas.width * math.tau
        rise = sum(weight * math.sin(freq * phase + shift) for freq, shift, weight in waves)
        points.append((float(column), canvas.height * baseline - rise * amplitude * canvas.unit))
    return points


def tree(pen: ImageDraw.ImageDraw, canvas: Canvas, base: Point, size: float, color: Rgb) -> None:
    x, y = base
    trunk = (x - size * 0.12, y - size * 0.9, x + size * 0.12, y + size * 0.1)
    pen.rectangle(trunk, fill=(*TRUNK, 255), **canvas.inked())
    crown = (x - size * 0.6, y - size * 1.9, x + size * 0.6, y - size * 0.7)
    pen.ellipse(crown, fill=(*color, 255), **canvas.inked())


def flower(pen: ImageDraw.ImageDraw, canvas: Canvas, base: Point, size: float, color: Rgb) -> None:
    pen.ellipse(circle(base, size), fill=(*color, 255), **canvas.inked())
    pen.ellipse(circle(base, size * 0.4), fill=(255, 236, 140))


def hills(image: Image.Image, canvas: Canvas, palette: Palette, rng: random.Random) -> None:
    pen = ImageDraw.Draw(image)
    for layer, (baseline, color) in enumerate(zip((0.6, 0.72, 0.84), palette.hills, strict=True)):
        curve = hill_curve(canvas, rng, baseline, 6 - layer * 1.5)
        pen.polygon([*curve, (canvas.width, canvas.height), (0, canvas.height)], fill=(*color, 255))
        if canvas.ink is not None:
            pen.line(curve, fill=(*canvas.ink.color, 255), width=canvas.stroke, joint="curve")
        decorate(pen, canvas, curve, layer, palette, rng)


def decorate(
    pen: ImageDraw.ImageDraw,
    canvas: Canvas,
    curve: list[Point],
    layer: int,
    palette: Palette,
    rng: random.Random,
) -> None:
    if layer == 1:
        for point in rng.sample(curve, k=min(len(curve), rng.randint(3, 7))):
            base = (point[0], point[1] + canvas.unit)
            tree(pen, canvas, base, canvas.unit * rng.uniform(6, 10), palette.hills[2])
    if layer == 2:
        for point in rng.sample(curve, k=min(len(curve), rng.randint(6, 14))):
            depth = (point[0], point[1] + rng.uniform(2, 10) * canvas.unit)
            flower(pen, canvas, depth, canvas.unit * rng.uniform(1.0, 1.7), palette.accent)


def drawn_scene(style: SceneStyle, canvas: Canvas, rng: random.Random) -> Image.Image:
    palette = style.palette
    image = gradient(canvas, palette.sky_top, palette.sky_bottom)
    center = (rng.uniform(0.15, 0.85) * canvas.width, rng.uniform(0.14, 0.3) * canvas.height)
    glow(image, canvas, center, canvas.unit * rng.uniform(7, 10), palette.celestial)
    sky_details(image, canvas, palette, rng)
    hills(image, canvas, palette, rng)
    return image


def paint_scene(
    prompt: str,
    seed: int,
    size: tuple[int, int],
    supersample: int,
    hints: ImageStyleHints | None = None,
) -> Image.Image:
    rng = random.Random(seed)
    style = scene_style(prompt, rng, hints)
    canvas = Canvas(size[0] * supersample, size[1] * supersample, style.ink)
    image = drawn_scene(style, canvas, rng).convert("RGB")
    final = image.resize(size, Image.Resampling.LANCZOS)
    return textured(final, style.texture, seed, style.swatches())
