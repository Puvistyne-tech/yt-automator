from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from automator.infrastructure.providers.image.scene_palette import Palette, Rgb, palette_for

Point = tuple[float, float]


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int

    @property
    def unit(self) -> float:
        return min(self.width, self.height) / 100


def gradient(canvas: Canvas, top: Rgb, bottom: Rgb) -> Image.Image:
    ramp = np.linspace(0.0, 1.0, canvas.height)[:, None, None]
    colors = np.array(top)[None, None, :] * (1 - ramp) + np.array(bottom)[None, None, :] * ramp
    rows = np.repeat(colors, canvas.width, axis=1).astype(np.uint8)
    return Image.fromarray(rows).convert("RGBA")


def glow(image: Image.Image, center: Point, radius: float, color: Rgb) -> None:
    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pen = ImageDraw.Draw(halo)
    for step in range(4, 0, -1):
        reach = radius * (1 + step * 0.45)
        box = (center[0] - reach, center[1] - reach, center[0] + reach, center[1] + reach)
        pen.ellipse(box, fill=(*color, 28))
    image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(radius * 0.6)))
    ImageDraw.Draw(image).ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=(*color, 255),
    )


def sky_details(image: Image.Image, canvas: Canvas, palette: Palette, rng: random.Random) -> None:
    pen = ImageDraw.Draw(image)
    if palette.night:
        for _ in range(int(canvas.width * canvas.height / (canvas.unit**2 * 120)) + 20):
            x, y = rng.uniform(0, canvas.width), rng.uniform(0, canvas.height * 0.55)
            size = rng.uniform(0.15, 0.45) * canvas.unit
            pen.ellipse((x - size, y - size, x + size, y + size), fill=(255, 250, 220, 230))
        return
    for _ in range(rng.randint(2, 4)):
        cloud(pen, canvas, rng)


def cloud(pen: ImageDraw.ImageDraw, canvas: Canvas, rng: random.Random) -> None:
    x, y = rng.uniform(0, canvas.width), rng.uniform(0.08, 0.32) * canvas.height
    size = rng.uniform(5, 9) * canvas.unit
    for offset in (-1.1, -0.4, 0.4, 1.1):
        lift = size * (0.55 if abs(offset) < 1 else 0.25)
        box = (x + offset * size - size * 0.7, y - lift - size * 0.5)
        pen.ellipse((*box, box[0] + size * 1.4, y + size * 0.45), fill=(255, 255, 255, 215))


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


def tree(pen: ImageDraw.ImageDraw, base: Point, size: float, color: Rgb) -> None:
    x, y = base
    trunk = (110, 78, 52, 255)
    pen.rectangle((x - size * 0.12, y - size * 0.9, x + size * 0.12, y + size * 0.1), fill=trunk)
    pen.ellipse(
        (x - size * 0.6, y - size * 1.9, x + size * 0.6, y - size * 0.7), fill=(*color, 255)
    )


def flower(pen: ImageDraw.ImageDraw, base: Point, size: float, color: Rgb) -> None:
    x, y = base
    pen.ellipse((x - size, y - size, x + size, y + size), fill=(*color, 255))
    pen.ellipse(
        (x - size * 0.4, y - size * 0.4, x + size * 0.4, y + size * 0.4), fill=(255, 236, 140)
    )


def hills(image: Image.Image, canvas: Canvas, palette: Palette, rng: random.Random) -> None:
    pen = ImageDraw.Draw(image)
    for layer, (baseline, color) in enumerate(zip((0.6, 0.72, 0.84), palette.hills, strict=True)):
        curve = hill_curve(canvas, rng, baseline, 6 - layer * 1.5)
        pen.polygon([*curve, (canvas.width, canvas.height), (0, canvas.height)], fill=(*color, 255))
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
            leaf = palette.hills[2]
            tree(pen, (point[0], point[1] + canvas.unit), canvas.unit * rng.uniform(6, 10), leaf)
    if layer == 2:
        for point in rng.sample(curve, k=min(len(curve), rng.randint(6, 14))):
            depth = (point[0], point[1] + rng.uniform(2, 10) * canvas.unit)
            flower(pen, depth, canvas.unit * rng.uniform(1.0, 1.7), palette.accent)


def paint_scene(prompt: str, seed: int, width: int, height: int, supersample: int) -> Image.Image:
    rng = random.Random(seed)
    palette = palette_for(prompt, rng)
    canvas = Canvas(width * supersample, height * supersample)
    image = gradient(canvas, palette.sky_top, palette.sky_bottom)
    center = (rng.uniform(0.15, 0.85) * canvas.width, rng.uniform(0.14, 0.3) * canvas.height)
    glow(image, center, canvas.unit * rng.uniform(7, 10), palette.celestial)
    sky_details(image, canvas, palette, rng)
    hills(image, canvas, palette, rng)
    return image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
