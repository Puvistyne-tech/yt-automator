from __future__ import annotations

from pathlib import Path

from autotube.domain.capabilities import VideoComposition
from autotube.infrastructure.providers.ffmpeg_args import ffmpeg_command
from autotube.infrastructure.providers.media.composition_audio import (
    LoudnessMeasurement,
    audio_graph,
    loudnorm,
)
from autotube.infrastructure.providers.media.composition_inputs import (
    plan_inputs,
    timeline_seconds,
)
from autotube.infrastructure.providers.media.composition_video import video_graph
from autotube.infrastructure.providers.media.encoder_quality import quality_crf
from autotube.infrastructure.providers.media.ffmpeg_options import FfmpegOptions


def measure_command(composition: VideoComposition, options: FfmpegOptions) -> list[str]:
    plan = plan_inputs(composition)
    total = timeline_seconds(composition)
    level = f"{loudnorm(composition, options, None)}:print_format=json"
    graph = ";".join(audio_graph(composition, plan, total, options, level))
    return ffmpeg_command(
        options.ffmpeg_binary,
        *plan.args,
        "-filter_complex",
        graph,
        "-map",
        "[aout]",
        "-vn",
        "-f",
        "null",
        "-",
        quiet_errors=False,
    )


def encoding_args(composition: VideoComposition, options: FfmpegOptions) -> list[str]:
    return [
        "-c:v",
        "libx264",
        "-preset",
        options.preset,
        "-crf",
        str(quality_crf(options.crf, composition.quality)),
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(composition.fps),
        "-c:a",
        "aac",
        "-b:a",
        options.audio_bitrate,
        "-ar",
        str(options.sample_rate),
        "-movflags",
        "+faststart",
    ]


def compose_command(
    composition: VideoComposition,
    options: FfmpegOptions,
    output: Path,
    measured: LoudnessMeasurement | None,
    normalise: bool,
) -> list[str]:
    plan = plan_inputs(composition)
    total = timeline_seconds(composition)
    level = loudnorm(composition, options, measured) if normalise else None
    chains = [
        *video_graph(composition, plan, total, options),
        *audio_graph(composition, plan, total, options, level),
    ]
    return ffmpeg_command(
        options.ffmpeg_binary,
        *plan.args,
        "-filter_complex",
        ";".join(chains),
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        *encoding_args(composition, options),
        "-t",
        f"{total:.3f}",
        str(output),
    )


def probe_duration_command(media: Path, options: FfmpegOptions) -> list[str]:
    return [
        options.ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media),
    ]


def frame_command(
    video: Path, at_seconds: float, output: Path, options: FfmpegOptions
) -> list[str]:
    return ffmpeg_command(
        options.ffmpeg_binary,
        "-ss",
        f"{at_seconds:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        str(options.frame_quality),
        str(output),
    )


def loudness_command(media: Path, options: FfmpegOptions) -> list[str]:
    return ffmpeg_command(
        options.ffmpeg_binary,
        "-i",
        str(media),
        "-map",
        "0:a:0",
        "-filter:a",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
        quiet_errors=False,
    )
