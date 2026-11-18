from __future__ import annotations

from pathlib import Path

import pytest
from PIL import ImageFont


def bundled_pillow_font() -> ImageFont.FreeTypeFont:
    font = ImageFont.load_default(12)
    if not isinstance(font, ImageFont.FreeTypeFont):
        pytest.skip("Pillow was built without FreeType, so it has no font file to measure with")
    return font


def embedded_font(folder: Path) -> Path:
    path = folder / "embedded.ttf"
    path.write_bytes(bundled_pillow_font().font_bytes)
    return path


def embedded_font_family() -> str:
    return str(bundled_pillow_font().getname()[0])
