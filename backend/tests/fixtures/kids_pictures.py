from __future__ import annotations

from pathlib import Path

from PIL import Image

from automator.domain.run_parts import Artifact


def single_colour(image: Image.Image) -> bool:
    return image.convert("RGB").getcolors(maxcolors=1) is not None


def is_solid(path: Path) -> bool:
    with Image.open(path) as image:
        return single_colour(image)


def corner_is_solid(path: Path) -> bool:
    with Image.open(path) as image:
        return single_colour(image.crop((0, 0, image.width // 2, image.height // 3)))


def scene_visual_files(root: Path, visuals: list[Artifact], variant: str) -> list[Path]:
    return [
        root / item.filename for item in visuals if item.variant == variant and "scene" in item.meta
    ]
