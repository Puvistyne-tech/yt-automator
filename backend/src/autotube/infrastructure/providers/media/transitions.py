from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.capabilities import TimedClip
from autotube.domain.video_look import Transition
from autotube.infrastructure.providers.media.composition_inputs import clip_end

WITH_ALPHA = "format=yuva420p"


def overlap(before: TimedClip, after: TimedClip) -> float:
    return max(0.0, round(clip_end(before) - after.start_seconds, 3))


def overlaps(clips: Sequence[TimedClip]) -> list[float]:
    inner = [overlap(before, after) for before, after in zip(clips, clips[1:], strict=False)]
    return [0.0, *inner, 0.0]


def reveal(start: float, seconds: float) -> list[str]:
    return [WITH_ALPHA, f"fade=t=in:st={start:.3f}:d={seconds:.3f}:alpha=1"]


def crossfade_steps(clip: TimedClip, incoming: float) -> list[str]:
    return reveal(clip.start_seconds, incoming) if incoming > 0 else []


def through_black_steps(clip: TimedClip, incoming: float, outgoing: float) -> list[str]:
    steps: list[str] = []
    if outgoing > 0:
        start = clip_end(clip) - outgoing
        steps.append(f"fade=t=out:st={start:.3f}:d={outgoing / 2:.3f}")
    if incoming > 0:
        steps.extend(reveal(clip.start_seconds + incoming / 2, incoming / 2))
    return steps


def transition_steps(
    transition: Transition, clip: TimedClip, incoming: float, outgoing: float
) -> list[str]:
    if transition is Transition.CROSSFADE:
        return crossfade_steps(clip, incoming)
    if transition is Transition.FADE_THROUGH_BLACK:
        return through_black_steps(clip, incoming, outgoing)
    return []
