from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import JsonValue

from automator.domain.capabilities import SubtitleStyle, TimedClip, VideoComposition
from automator.pipelines.kids_story.artifacts import SHORT, is_scene_key
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.subtitles.layout import subtitle_layout
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.voices import VoiceLine


@dataclass(frozen=True)
class Sources:
    workspace: Path
    clips: Mapping[str, Path]
    voices: Mapping[str, VoiceLine]
    effects: Mapping[str, Path]
    music: Path | None
    subtitles: Path | None


def visual_clips(segments: Sequence[Segment], sources: Sources) -> tuple[TimedClip, ...]:
    return tuple(
        TimedClip(
            path=sources.clips[item.visual_key],
            start_seconds=item.start,
            duration_seconds=item.duration,
        )
        for item in segments
    )


def narration_clips(segments: Sequence[Segment], sources: Sources) -> tuple[TimedClip, ...]:
    return tuple(
        TimedClip(
            path=sources.workspace / line.filename,
            start_seconds=item.narration_start,
            duration_seconds=line.seconds,
        )
        for item in segments
        if item.narration is not None and (line := sources.voices.get(item.key)) is not None
    )


def effect_clips(
    segments: Sequence[Segment], story: Story, sources: Sources, settings: KidsStorySettings
) -> tuple[TimedClip, ...]:
    effects = settings.sound_effects
    if not effects.enabled:
        return ()
    return tuple(
        TimedClip(
            path=sources.effects[cue],
            start_seconds=item.start + effects.offset_seconds,
            duration_seconds=effects.duration_seconds,
            volume=effects.volume,
        )
        for item in segments
        if item.scene is not None and is_scene_key(item.key)
        for cue in story.scenes[item.scene].sound_effects
        if cue in sources.effects
    )


def subtitle_style(settings: KidsStorySettings, language: str, variant: str) -> SubtitleStyle:
    subtitles = settings.subtitles
    layout = subtitle_layout(settings, language, variant)
    return SubtitleStyle(
        burn_in=subtitles.burn_in_short if variant == SHORT else subtitles.burn_in_episode,
        font_family=layout.font.family,
        font_file=layout.font.file,
        font_size=layout.font_size,
        primary_color=subtitles.primary_color,
        outline_color=subtitles.outline_color,
        highlight_color=subtitles.highlight_color,
        margin_bottom=layout.bottom_margin,
        margin_sides=layout.side_margin,
    )


def composition(
    segments: Sequence[Segment],
    story: Story,
    sources: Sources,
    settings: KidsStorySettings,
    variant: str,
) -> VideoComposition:
    width, height = settings.video_size(variant)
    return VideoComposition(
        width=width,
        height=height,
        fps=settings.episode.fps,
        visuals=visual_clips(segments, sources),
        narration=narration_clips(segments, sources),
        music=sources.music,
        music_volume=settings.music.volume,
        music_ducking=settings.music.ducking,
        sound_effects=effect_clips(segments, story, sources, settings),
        subtitles=sources.subtitles,
        subtitle_style=subtitle_style(settings, story.language, variant),
        loudness_lufs=settings.episode.loudness_lufs,
        fade_seconds=settings.episode.fade_seconds,
    )


def timeline_meta(segments: Sequence[Segment]) -> list[JsonValue]:
    return [
        {"key": item.key, "start": item.start, "duration": item.duration, "scene": item.scene}
        for item in segments
    ]
