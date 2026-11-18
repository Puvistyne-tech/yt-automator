from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from autotube.shared.errors import UpstreamFailure


def rounded_up(value: int, multiple: int) -> int:
    return max(multiple, -(-value // multiple) * multiple)


def fit_image(path: Path, width: int, height: int) -> Path:
    try:
        with Image.open(path) as source:
            if source.size == (width, height):
                return path
            fitted = ImageOps.fit(source.convert("RGB"), (width, height), Image.Resampling.LANCZOS)
        fitted.save(path)
    except OSError as error:
        raise UpstreamFailure(f"generated image {path.name} is unreadable: {error}") from error
    return path
