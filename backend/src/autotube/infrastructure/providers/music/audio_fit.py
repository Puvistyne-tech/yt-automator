from __future__ import annotations

from pathlib import Path

from pydantic import Field

from autotube.infrastructure.providers.ffmpeg_args import FfmpegBinaryOptions, ffmpeg_command


class AudioFitOptions(FfmpegBinaryOptions):
    fade_seconds: float = Field(
        default=1.5, ge=0.0, title="Fade", description="Fade in and fade out length in seconds."
    )
    sample_rate: int = Field(
        default=44100, ge=8000, le=96000, title="Sample rate", description="Output rate in Hz."
    )
    timeout_seconds: float = Field(
        default=300.0, gt=0, title="Timeout", description="Seconds allowed for fitting the track."
    )


def fade_filter(duration: float, fade_seconds: float) -> str:
    fade = min(fade_seconds, duration / 2)
    if fade <= 0:
        return "anull"
    out_start = round(duration - fade, 3)
    return f"afade=t=in:st=0:d={fade:.3f},afade=t=out:st={out_start}:d={fade:.3f}"


def fit_audio_command(
    source: Path, output: Path, duration: float, options: AudioFitOptions
) -> list[str]:
    return ffmpeg_command(
        options.ffmpeg_binary,
        "-stream_loop",
        "-1",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-af",
        fade_filter(duration, options.fade_seconds),
        "-ar",
        str(options.sample_rate),
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(output),
    )
