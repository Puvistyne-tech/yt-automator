from __future__ import annotations

from pathlib import Path

from automator.domain.capabilities import Capability, VideoComposition
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.host import first_reason
from automator.infrastructure.providers.media.composition_audio import LoudnessMeasurement
from automator.infrastructure.providers.media.ffmpeg_options import FfmpegOptions
from automator.infrastructure.providers.media.loudness import parse_integrated, parse_loudnorm
from automator.infrastructure.providers.media.media_commands import (
    compose_command,
    frame_command,
    loudness_command,
    measure_command,
    probe_duration_command,
)
from automator.infrastructure.providers.output_path import ensure_parent, require_written
from automator.infrastructure.providers.spec import ProviderSpec
from automator.shared.errors import UpstreamFailure


def has_audio(composition: VideoComposition) -> bool:
    return bool(composition.narration or composition.sound_effects or composition.music)


class FfmpegMedia:
    provider_id = "ffmpeg"

    def __init__(self, options: FfmpegOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        host = self.context.host
        return first_reason(
            host.missing_binary(self.options.ffmpeg_binary),
            host.missing_binary(self.options.ffprobe_binary),
        )

    def run(self, command: list[str], timeout: float | None = None) -> str:
        limit = timeout or self.options.probe_timeout_seconds
        return self.context.runner.run(command, limit).stderr

    def duration_seconds(self, media: Path) -> float:
        command = probe_duration_command(media, self.options)
        stdout = self.context.runner.run(command, self.options.probe_timeout_seconds).stdout
        try:
            return float(stdout.strip())
        except ValueError as error:
            raise UpstreamFailure(f"ffprobe found no duration in {media.name}") from error

    def measured(self, composition: VideoComposition) -> LoudnessMeasurement | None:
        stderr = self.run(measure_command(composition, self.options), self.options.timeout_seconds)
        return parse_loudnorm(stderr)

    def compose_video(self, composition: VideoComposition, output: Path) -> Path:
        if not composition.visuals:
            raise UpstreamFailure("a video needs at least one visual clip")
        measurement = None
        normalise = has_audio(composition)
        if normalise and self.options.two_pass_loudness:
            measurement = self.measured(composition)
            normalise = measurement is not None
        ensure_parent(output)
        command = compose_command(composition, self.options, output, measurement, normalise)
        self.run(command, self.options.timeout_seconds)
        return output

    def extract_frame(self, video: Path, at_seconds: float, output: Path) -> Path:
        self.run(frame_command(video, at_seconds, ensure_parent(output), self.options))
        return require_written(output, f"ffmpeg frame at {at_seconds:g}s")

    def loudness_lufs(self, media: Path) -> float:
        return parse_integrated(self.run(loudness_command(media, self.options)))


SPEC = ProviderSpec(
    provider_id=FfmpegMedia.provider_id,
    capability=Capability.MEDIA,
    name="ffmpeg",
    description="Composes, mixes, subtitles and measures video with ffmpeg and ffprobe.",
    options=FfmpegOptions,
    factory=FfmpegMedia,
    offline=True,
)
