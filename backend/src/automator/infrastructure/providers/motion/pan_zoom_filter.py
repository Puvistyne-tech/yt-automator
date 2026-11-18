from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automator.domain.capabilities import CameraMove, MotionRequest
from automator.infrastructure.providers.ffmpeg_args import ffmpeg_command

CENTER_X = "(iw-iw/zoom)/2"
CENTER_Y = "(ih-ih/zoom)/2"


@dataclass(frozen=True)
class PanZoomTuning:
    max_zoom: float
    supersample: int
    crf: int
    preset: str


def frame_count(request: MotionRequest) -> int:
    return max(1, round(request.duration_seconds * request.fps))


def eased_progress(frames: int) -> str:
    progress = f"(on/{max(frames - 1, 1)})"
    return f"({progress}*{progress}*(3-2*{progress}))"


def camera_expressions(camera: CameraMove, extra: float, ease: str) -> tuple[str, str, str]:
    held = f"{1 + extra:.4f}"
    travel_x = "(iw-iw/zoom)"
    travel_y = "(ih-ih/zoom)"
    table = {
        CameraMove.PUSH_IN: (f"1+{extra:.4f}*{ease}", CENTER_X, CENTER_Y),
        CameraMove.PULL_OUT: (f"1+{extra:.4f}*(1-{ease})", CENTER_X, CENTER_Y),
        CameraMove.PAN_LEFT: (held, f"{travel_x}*(1-{ease})", CENTER_Y),
        CameraMove.PAN_RIGHT: (held, f"{travel_x}*{ease}", CENTER_Y),
        CameraMove.RISE: (held, CENTER_X, f"{travel_y}*(1-{ease})"),
        CameraMove.STILL: ("1", CENTER_X, CENTER_Y),
    }
    return table[camera]


def pan_zoom_filter(request: MotionRequest, tuning: PanZoomTuning) -> str:
    frames = frame_count(request)
    extra = tuning.max_zoom * request.intensity
    zoom, x, y = camera_expressions(request.camera, extra, eased_progress(frames))
    wide, tall = request.width * tuning.supersample, request.height * tuning.supersample
    return ",".join(
        [
            f"scale={wide}:{tall}:force_original_aspect_ratio=increase:flags=lanczos",
            f"crop={wide}:{tall}",
            f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}"
            f":s={request.width}x{request.height}:fps={request.fps}",
            "format=yuv420p",
        ]
    )


def pan_zoom_command(
    request: MotionRequest, tuning: PanZoomTuning, binary: str, output: Path
) -> list[str]:
    return ffmpeg_command(
        binary,
        "-i",
        str(request.image),
        "-vf",
        pan_zoom_filter(request, tuning),
        "-frames:v",
        str(frame_count(request)),
        "-r",
        str(request.fps),
        "-c:v",
        "libx264",
        "-preset",
        tuning.preset,
        "-crf",
        str(tuning.crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    )
