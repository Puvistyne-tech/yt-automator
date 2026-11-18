from __future__ import annotations

from pathlib import Path

from autotube.domain.video_look import ScreenCorner, Watermark
from autotube.pipelines.kids_story.artifacts import SHORT
from autotube.pipelines.kids_story.settings.media import VisualSettings

PERCENT = 100


class LogoMissingError(FileNotFoundError):
    pass


def wants_logo(visuals: VisualSettings, variant: str) -> bool:
    shown = visuals.logo_on_short if variant == SHORT else visuals.logo_on_episode
    return shown and bool(visuals.logo_file)


def logo_path(visuals: VisualSettings) -> Path:
    path = Path(visuals.logo_file).expanduser()
    if not path.is_file():
        raise LogoMissingError(
            f"visuals.logo_file: no picture at {visuals.logo_file!r}; choose an existing "
            "logo file or clear the field"
        )
    return path


def video_watermark(visuals: VisualSettings, variant: str) -> Watermark | None:
    if not wants_logo(visuals, variant):
        return None
    return Watermark(
        image=logo_path(visuals),
        corner=ScreenCorner(visuals.logo_corner.value),
        width_share=visuals.logo_size_percent / PERCENT,
        opacity=visuals.logo_opacity,
        margin_share=visuals.logo_margin_percent / PERCENT,
    )
