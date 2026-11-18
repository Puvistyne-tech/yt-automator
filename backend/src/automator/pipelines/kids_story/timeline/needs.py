from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from automator.pipelines.kids_story.timeline.cuts import Cut
from automator.pipelines.kids_story.timeline.plan import Segment


class ClipNeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    visual_key: str
    variant: str
    seconds: float
    scene: int | None = None


def variant_of(visual_key: str) -> str:
    return visual_key.rpartition("@")[2]


def merged(current: ClipNeed | None, segment: Segment) -> ClipNeed:
    if current is None:
        return ClipNeed(
            visual_key=segment.visual_key,
            variant=variant_of(segment.visual_key),
            seconds=segment.duration,
            scene=segment.scene,
        )
    return current.model_copy(
        update={
            "seconds": max(current.seconds, segment.duration),
            "scene": current.scene if current.scene is not None else segment.scene,
        }
    )


def clip_needs(cuts: Sequence[Cut]) -> dict[str, ClipNeed]:
    needs: dict[str, ClipNeed] = {}
    for cut in cuts:
        for segment in cut.segments:
            needs[segment.visual_key] = merged(needs.get(segment.visual_key), segment)
    return needs
