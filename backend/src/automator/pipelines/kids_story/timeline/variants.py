from __future__ import annotations

from collections.abc import Mapping

from automator.pipelines.kids_story.artifacts import (
    EPISODE,
    SHORT,
    scene_key,
    scene_visual_key,
    visual_key,
)
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.plan import (
    Padding,
    Segment,
    SegmentSpec,
    fit_within,
    laid_out,
)
from automator.pipelines.kids_story.timeline.selection import short_scene_indexes
from automator.pipelines.kids_story.timeline.voices import VoiceLine

INTRO = "intro"
OUTRO = "outro"
HOOK = "hook"


def padding_of(settings: KidsStorySettings) -> Padding:
    episode = settings.episode
    return Padding(lead_in=episode.scene_lead_in_seconds, tail=episode.scene_tail_seconds)


def card_key(card: str, language: str) -> str:
    return visual_key(f"card-{card}-{language}", EPISODE)


def spec(
    key: str, visual: str, voices: Mapping[str, VoiceLine], minimum: float, scene: int | None
) -> SegmentSpec:
    line = voices.get(key)
    return SegmentSpec(
        key=key,
        visual_key=visual,
        narration=line.filename if line else None,
        narration_seconds=line.seconds if line else 0.0,
        min_seconds=minimum,
        scene=scene,
    )


def has_card(card: str, settings: KidsStorySettings) -> bool:
    return settings.episode.intro_card if card == INTRO else settings.episode.outro_card


def card_spec(
    card: str, story: Story, voices: Mapping[str, VoiceLine], settings: KidsStorySettings
) -> SegmentSpec | None:
    if has_card(card, settings):
        visual = card_key(card, story.language)
        return spec(card, visual, voices, settings.episode.card_seconds, None)
    if card not in voices:
        return None
    fallback = 0 if card == INTRO else len(story.scenes) - 1
    visual = scene_visual_key(fallback, EPISODE)
    return spec(card, visual, voices, settings.episode.min_scene_seconds, None)


def episode_specs(
    story: Story, voices: Mapping[str, VoiceLine], settings: KidsStorySettings
) -> list[SegmentSpec]:
    minimum = settings.episode.min_scene_seconds
    scenes = [
        spec(scene_key(index), scene_visual_key(index, EPISODE), voices, minimum, index)
        for index in range(len(story.scenes))
    ]
    intro = card_spec(INTRO, story, voices, settings)
    outro = card_spec(OUTRO, story, voices, settings)
    return [*([intro] if intro else []), *scenes, *([outro] if outro else [])]


def short_specs(
    story: Story, voices: Mapping[str, VoiceLine], settings: KidsStorySettings
) -> list[SegmentSpec]:
    indexes = short_scene_indexes(story, settings.short)
    minimum = settings.episode.min_scene_seconds
    scenes = [
        spec(scene_key(index), scene_visual_key(index, SHORT), voices, minimum, index)
        for index in indexes
    ]
    hook: list[SegmentSpec] = []
    if settings.short.hook_line and HOOK in voices and indexes:
        first = scene_visual_key(indexes[0], SHORT)
        hook = [spec(HOOK, first, voices, minimum, None)]
    padding = padding_of(settings)
    return fit_within([*hook, *scenes], padding, settings.short.max_duration_seconds)


def planned(
    story: Story, voices: Mapping[str, VoiceLine], settings: KidsStorySettings, variant: str
) -> list[Segment]:
    if variant == SHORT:
        specs = short_specs(story, voices, settings) if settings.short.enabled else []
    else:
        specs = episode_specs(story, voices, settings)
    if variant == SHORT and not any(item.scene is not None for item in specs):
        return []
    return laid_out(specs, padding_of(settings))
