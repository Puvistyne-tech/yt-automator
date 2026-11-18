from __future__ import annotations

from pydantic import Field

from autotube.infrastructure.providers.spec import ProviderOptions

QUIET_PREFIX = ("-y", "-hide_banner", "-loglevel", "error")
REPORTING_PREFIX = ("-hide_banner", "-nostats")


class FfmpegBinaryOptions(ProviderOptions):
    ffmpeg_binary: str = Field(
        default="ffmpeg", min_length=1, title="ffmpeg command", description="ffmpeg executable."
    )


class X264Options(FfmpegBinaryOptions):
    crf: int = Field(default=20, ge=0, le=51, title="Quality (CRF)", description="Lower is better.")
    preset: str = Field(
        default="medium", title="x264 preset", description="Encoder speed versus compression."
    )


def ffmpeg_command(binary: str, *args: str, quiet_errors: bool = True) -> list[str]:
    prefix = QUIET_PREFIX if quiet_errors else REPORTING_PREFIX
    return [binary, *prefix, *args]
