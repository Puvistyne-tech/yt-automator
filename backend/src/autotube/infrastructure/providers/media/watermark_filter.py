from __future__ import annotations

from autotube.domain.video_look import ScreenCorner, Watermark
from autotube.infrastructure.providers.even_size import even

LOGO_LABEL = "logo"
MARKED_LABEL = "marked"
LEFT_CORNERS = frozenset({ScreenCorner.TOP_LEFT, ScreenCorner.BOTTOM_LEFT})
TOP_CORNERS = frozenset({ScreenCorner.TOP_LEFT, ScreenCorner.TOP_RIGHT})


def logo_chain(index: int, watermark: Watermark, size: tuple[int, int]) -> str:
    width = even(round(size[0] * watermark.width_share))
    steps = [
        f"scale={width}:-2",
        "format=rgba",
        f"colorchannelmixer=aa={watermark.opacity:.3f}",
    ]
    return f"[{index}:v]{','.join(steps)}[{LOGO_LABEL}]"


def logo_place(watermark: Watermark, size: tuple[int, int]) -> str:
    margin = round(size[1] * watermark.margin_share)
    x = f"{margin}" if watermark.corner in LEFT_CORNERS else f"W-w-{margin}"
    y = f"{margin}" if watermark.corner in TOP_CORNERS else f"H-h-{margin}"
    return f"x={x}:y={y}"


def watermark_chains(
    index: int, watermark: Watermark, size: tuple[int, int], current: str
) -> list[str]:
    placed = f"[{current}][{LOGO_LABEL}]overlay={logo_place(watermark, size)}[{MARKED_LABEL}]"
    return [logo_chain(index, watermark, size), placed]
