from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from autotube.domain.capabilities import TimedClip, VideoComposition

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})


@dataclass
class InputPlan:
    args: list[str] = field(default_factory=list)
    visuals: list[int] = field(default_factory=list)
    narration: list[int] = field(default_factory=list)
    effects: list[int] = field(default_factory=list)
    music: int | None = None
    watermark: int | None = None
    count: int = 0

    def add(self, *args: str) -> int:
        self.args.extend(args)
        self.count += 1
        return self.count - 1


def is_still(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_SUFFIXES


def clip_end(clip: TimedClip) -> float:
    return clip.start_seconds + clip.duration_seconds


def timeline_seconds(composition: VideoComposition) -> float:
    clips = (*composition.visuals, *composition.narration, *composition.sound_effects)
    return round(max(clip_end(clip) for clip in clips), 3)


def visual_input(clip: TimedClip, fps: int) -> tuple[str, ...]:
    if is_still(clip.path):
        seconds = f"{clip.duration_seconds:.3f}"
        return ("-loop", "1", "-framerate", str(fps), "-t", seconds, "-i", str(clip.path))
    return ("-i", str(clip.path))


def plan_inputs(composition: VideoComposition) -> InputPlan:
    plan = InputPlan()
    for clip in composition.visuals:
        plan.visuals.append(plan.add(*visual_input(clip, composition.fps)))
    for clip in composition.narration:
        plan.narration.append(plan.add("-i", str(clip.path)))
    for clip in composition.sound_effects:
        plan.effects.append(plan.add("-i", str(clip.path)))
    if composition.music is not None:
        plan.music = plan.add("-stream_loop", "-1", "-i", str(composition.music))
    if composition.watermark is not None:
        plan.watermark = plan.add("-i", str(composition.watermark.image))
    return plan
