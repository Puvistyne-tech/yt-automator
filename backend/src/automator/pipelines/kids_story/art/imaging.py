from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

ImageFailure = (OSError, UnidentifiedImageError, ValueError)
QUALITY_STEP = 5


@dataclass(frozen=True)
class JpegBudget:
    max_bytes: int
    quality: int
    min_quality: int


def cover(image: Image.Image, width: int, height: int, focus: float) -> Image.Image:
    return ImageOps.fit(
        image.convert("RGB"),
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(min(max(focus, 0.0), 1.0), 0.5),
    )


def covered_copy(source: Path, output: Path, size: tuple[int, int], focus: float) -> Path | None:
    try:
        with Image.open(source) as image:
            cover(image, size[0], size[1], focus).save(output, format="PNG")
    except ImageFailure:
        return None
    return output


def qualities(budget: JpegBudget) -> list[int]:
    stepped = list(range(budget.quality, budget.min_quality, -QUALITY_STEP))
    return [*stepped, budget.min_quality]


def jpeg_bytes(image: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def saved_jpeg(source: Path, output: Path, budget: JpegBudget) -> int:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    for quality in qualities(budget):
        data = jpeg_bytes(image, quality)
        if len(data) <= budget.max_bytes:
            break
    output.write_bytes(data)
    return quality
