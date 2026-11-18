from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from PIL import Image, ImageFilter

from autotube.domain.image_style import Texture
from autotube.infrastructure.providers.image.scene_palette import Rgb

PIXEL_COLUMNS = 96
Treatment = Callable[[Image.Image, np.random.Generator, Sequence[Rgb]], Image.Image]


def blotches(size: tuple[int, int], rng: np.random.Generator, cell: int) -> np.ndarray:
    small = rng.normal(0.0, 1.0, (max(2, size[1] // cell), max(2, size[0] // cell)))
    field = Image.fromarray(((small.clip(-3, 3) + 3) / 6 * 255).astype(np.uint8))
    upscaled = field.resize(size, Image.Resampling.BICUBIC)
    return np.asarray(upscaled, dtype=np.float32) / 255 * 2 - 1


def shaded(image: Image.Image, light: np.ndarray, strength: float) -> Image.Image:
    pixels = np.asarray(image, dtype=np.float32)
    lit = pixels * (1 + light[..., None] * strength)
    return Image.fromarray(lit.clip(0, 255).astype(np.uint8))


def fine_noise(image: Image.Image, rng: np.random.Generator, spread: float) -> Image.Image:
    grain = rng.normal(0.0, spread, (image.height, image.width))
    pixels = np.asarray(image, dtype=np.float32) + grain[..., None]
    return Image.fromarray(pixels.clip(0, 255).astype(np.uint8))


def smooth(image: Image.Image, rng: np.random.Generator, colours: Sequence[Rgb]) -> Image.Image:
    del rng, colours
    return image


def paper(image: Image.Image, rng: np.random.Generator, colours: Sequence[Rgb]) -> Image.Image:
    del colours
    washed = shaded(image, blotches(image.size, rng, 24), 0.07)
    return fine_noise(washed, rng, 5.0)


def grain(image: Image.Image, rng: np.random.Generator, colours: Sequence[Rgb]) -> Image.Image:
    del colours
    return fine_noise(image, rng, 14.0)


def clay(image: Image.Image, rng: np.random.Generator, colours: Sequence[Rgb]) -> Image.Image:
    del colours
    softened = image.filter(ImageFilter.GaussianBlur(max(1.0, image.width / 400)))
    lumpy = shaded(softened, blotches(image.size, rng, 10), 0.12)
    relief = lumpy.filter(ImageFilter.EMBOSS).convert("L").convert("RGB")
    return Image.blend(lumpy, relief, 0.18)


def pixel(image: Image.Image, rng: np.random.Generator, colours: Sequence[Rgb]) -> Image.Image:
    del rng
    columns = min(PIXEL_COLUMNS, image.width)
    rows = max(1, round(image.height * columns / image.width))
    small = image.resize((columns, rows), Image.Resampling.BOX)
    if colours:
        swatch = Image.new("P", (1, 1))
        padded = [colours[index % len(colours)] for index in range(256)]
        swatch.putpalette([channel for colour in padded for channel in colour])
        small = small.quantize(palette=swatch, dither=Image.Dither.NONE).convert("RGB")
    return small.resize(image.size, Image.Resampling.NEAREST)


TREATMENTS: dict[Texture, Treatment] = {
    Texture.SMOOTH: smooth,
    Texture.PAPER: paper,
    Texture.GRAIN: grain,
    Texture.CLAY: clay,
    Texture.PIXEL: pixel,
}


def textured(
    image: Image.Image, texture: Texture, seed: int, colours: Sequence[Rgb]
) -> Image.Image:
    rng = np.random.default_rng(seed)
    return TREATMENTS[texture](image.convert("RGB"), rng, colours)
