from __future__ import annotations

from pathlib import Path

from autotube.domain.video_look import ScreenCorner, Watermark
from autotube.pipelines.narrated_video.artifacts import SHORT
from autotube.pipelines.narrated_video.settings.media import VisualSettings

PERCENT = 100


def wants_logo(visuals: VisualSettings, variant: str) -> bool:
    shown = visuals.logo_on_short if variant == SHORT else visuals.logo_on_episode
    return shown and bool(visuals.logo_file)


def video_watermark(visuals: VisualSettings, variant: str) -> Watermark | None:
    if not wants_logo(visuals, variant):
        return None
    return Watermark(
        image=Path(visuals.logo_file).expanduser(),
        corner=ScreenCorner(visuals.logo_corner.value),
        width_share=visuals.logo_size_percent / PERCENT,
        opacity=visuals.logo_opacity,
        margin_share=visuals.logo_margin_percent / PERCENT,
    )
