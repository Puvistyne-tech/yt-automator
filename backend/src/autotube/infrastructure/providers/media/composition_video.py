from __future__ import annotations

from autotube.domain.capabilities import TimedClip, VideoComposition
from autotube.infrastructure.providers.even_size import even
from autotube.infrastructure.providers.media.composition_inputs import InputPlan
from autotube.infrastructure.providers.media.ffmpeg_options import FfmpegOptions
from autotube.infrastructure.providers.media.subtitle_filter import subtitle_filter


def frame_size(composition: VideoComposition) -> tuple[int, int]:
    return even(composition.width), even(composition.height)


def visual_chain(index: int, label: str, clip: TimedClip, composition: VideoComposition) -> str:
    width, height = frame_size(composition)
    size = f"{width}:{height}"
    seconds = f"{clip.duration_seconds:.3f}"
    steps = [
        f"scale={size}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={size}",
        "setsar=1",
        f"fps={composition.fps}",
        "format=yuv420p",
        f"tpad=stop_mode=clone:stop_duration={seconds}",
        f"trim=duration={seconds}",
        f"setpts=PTS-STARTPTS+{clip.start_seconds:.3f}/TB",
    ]
    return f"[{index}:v]{','.join(steps)}[{label}]"


def canvas_chain(composition: VideoComposition, total: float, options: FfmpegOptions) -> str:
    width, height = frame_size(composition)
    color = options.background_color
    size = f"{width}x{height}"
    return f"color=c={color}:s={size}:r={composition.fps}:d={total:.3f},format=yuv420p[base]"


def fade_steps(fade: float, total: float) -> list[str]:
    fade = min(fade, total / 2)
    if fade <= 0:
        return []
    return [f"fade=t=in:st=0:d={fade:.3f}", f"fade=t=out:st={total - fade:.3f}:d={fade:.3f}"]


def finishing_steps(composition: VideoComposition, total: float, options: FfmpegOptions) -> str:
    steps = []
    if composition.subtitles is not None and composition.subtitle_style.burn_in:
        steps.append(
            subtitle_filter(composition.subtitles, composition.subtitle_style, options.fonts_dir)
        )
    steps.extend(fade_steps(composition.fade_seconds, total))
    steps.append("format=yuv420p")
    return ",".join(steps)


def video_graph(
    composition: VideoComposition, plan: InputPlan, total: float, options: FfmpegOptions
) -> list[str]:
    chains = [canvas_chain(composition, total, options)]
    current = "base"
    pairs = zip(plan.visuals, composition.visuals, strict=True)
    for position, (index, clip) in enumerate(pairs):
        chains.append(visual_chain(index, f"v{position}", clip, composition))
        chains.append(f"[{current}][v{position}]overlay=eof_action=pass:repeatlast=0[o{position}]")
        current = f"o{position}"
    chains.append(f"[{current}]{finishing_steps(composition, total, options)}[vout]")
    return chains
