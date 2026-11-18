from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from automator.pipelines.kids_story.artifacts import VARIANTS
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.variants import planned
from automator.pipelines.kids_story.timeline.voices import VoiceLine


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


def clip_needs(
    plans: Sequence[tuple[Story, Mapping[str, VoiceLine]]], settings: KidsStorySettings
) -> dict[str, ClipNeed]:
    needs: dict[str, ClipNeed] = {}
    for story, voices in plans:
        for variant in VARIANTS:
            for segment in planned(story, voices, settings, variant):
                needs[segment.visual_key] = merged(needs.get(segment.visual_key), segment)
    return needs
