from __future__ import annotations

from pathlib import Path

from autotube.domain.capabilities import SubtitleStyle, TimedClip, VideoComposition
from autotube.infrastructure.providers.media.ffmpeg_options import FfmpegOptions

OPTIONS = FfmpegOptions()


def clip(name: str, start: float, seconds: float, volume: float = 1.0) -> TimedClip:
    return TimedClip(
        path=Path(f"/w/{name}"), start_seconds=start, duration_seconds=seconds, volume=volume
    )


def composition(**changes: object) -> VideoComposition:
    base = VideoComposition(
        width=320,
        height=180,
        fps=24,
        visuals=(clip("a.png", 0, 2), clip("b.mp4", 2, 1.5)),
        narration=(clip("n1.wav", 0.5, 1.0), clip("n2.wav", 2.0, 1.0, volume=0.8)),
        music=Path("/w/music.wav"),
        sound_effects=(clip("pop.wav", 1.0, 0.2),),
        subtitles=Path("/w/subs.ass"),
        subtitle_style=SubtitleStyle(burn_in=True, font_size=36, margin_bottom=40),
    )
    return base.model_copy(update=changes)
