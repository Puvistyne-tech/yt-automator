from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from autotube.domain.capabilities import MotionRequest
from autotube.infrastructure.providers.even_size import even
from autotube.infrastructure.providers.ffmpeg_args import ffmpeg_command, x264_args
from autotube.infrastructure.providers.home_path import home_expanded
from autotube.infrastructure.providers.motion.ltx_options import LtxOptions
from autotube.infrastructure.providers.motion.pan_zoom_filter import held_frames

FRAME_STEP = 8
LAST_FRAME_OFFSET = "-0.05"
ROUNDING_DIGITS = 6


@dataclass(frozen=True)
class Segment:
    image: Path
    frames: int
    output: Path


def segment_durations(total: float, longest: float) -> list[float]:
    count = max(1, math.ceil(round(total / longest, ROUNDING_DIGITS)))
    return [total / count] * count


def ltx_frame_count(seconds: float, frame_rate: int) -> int:
    needed = math.ceil(round(seconds * frame_rate, ROUNDING_DIGITS))
    steps = max(1, math.ceil((needed - 1) / FRAME_STEP))
    return steps * FRAME_STEP + 1


def generation_size(request: MotionRequest, options: LtxOptions) -> tuple[int, int]:
    if request.height > request.width:
        return options.portrait_width, options.portrait_height
    return options.landscape_width, options.landscape_height


def segment_plan(request: MotionRequest, options: LtxOptions, work: Path) -> list[Segment]:
    durations = segment_durations(request.duration_seconds, options.max_segment_seconds)
    return [
        Segment(
            image=request.image if index == 0 else work / f"start-{index}.png",
            frames=ltx_frame_count(seconds, options.frame_rate),
            output=work / f"segment-{index}.mp4",
        )
        for index, seconds in enumerate(durations)
    ]


def distilled_args(options: LtxOptions) -> list[str]:
    return ["--distilled"] if options.distilled else []


def text_encoder_args(options: LtxOptions) -> list[str]:
    return ["--gemma", options.text_encoder] if options.text_encoder else []


def guidance_args(request: MotionRequest, options: LtxOptions) -> list[str]:
    if not options.use_nag:
        return []
    return ["--nag", "--negative-prompt", request.negative_prompt or options.negative_prompt]


def ltx_command(request: MotionRequest, options: LtxOptions, segment: Segment) -> list[str]:
    width, height = generation_size(request, options)
    return [
        options.binary,
        "generate",
        *distilled_args(options),
        "--model",
        home_expanded(options.model_dir),
        *text_encoder_args(options),
        "--prompt",
        request.prompt,
        *guidance_args(request, options),
        "--image",
        str(segment.image),
        "0",
        str(options.image_strength),
        "-H",
        str(height),
        "-W",
        str(width),
        "-f",
        str(segment.frames),
        "--frame-rate",
        str(options.frame_rate),
        "--seed",
        str(options.seed),
        "--no-audio",
        "-o",
        str(segment.output),
    ]


def ltx_env(options: LtxOptions) -> dict[str, str]:
    home = {"HF_HOME": home_expanded(options.hf_home)} if options.hf_home else {}
    offline = {"HF_HUB_OFFLINE": "1"} if options.hf_offline else {}
    return {**home, **offline}


def last_frame_command(binary: str, clip: Path, output: Path) -> list[str]:
    return ffmpeg_command(
        binary, "-sseof", LAST_FRAME_OFFSET, "-i", str(clip), "-frames:v", "1", str(output)
    )


def finish_filter(request: MotionRequest, count: int) -> str:
    width, height = even(request.width), even(request.height)
    inputs = "".join(f"[{index}:v]" for index in range(count))
    return ",".join(
        [
            f"{inputs}concat=n={count}:v=1:a=0",
            f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos",
            f"crop={width}:{height}",
            "setsar=1",
            f"fps={request.fps}",
            *held_frames(request),
            "format=yuv420p",
        ]
    )


def finish_command(
    request: MotionRequest, options: LtxOptions, clips: list[Path], output: Path
) -> list[str]:
    inputs = [arg for clip in clips for arg in ("-i", str(clip))]
    return ffmpeg_command(
        options.ffmpeg_binary,
        *inputs,
        "-filter_complex",
        finish_filter(request, len(clips)),
        "-t",
        f"{request.duration_seconds:g}",
        "-r",
        str(request.fps),
        *x264_args(options.preset, options.crf),
        "-an",
        "-movflags",
        "+faststart",
        str(output),
    )
