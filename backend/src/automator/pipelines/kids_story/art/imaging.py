from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

ImageFailure = (OSError, UnidentifiedImageError, ValueError)


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
