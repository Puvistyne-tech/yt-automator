from __future__ import annotations

from collections.abc import Mapping, Sequence

from automator.pipelines.kids_story.artifacts import SHORT
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings
from automator.pipelines.kids_story.subtitles.cues import Cue, CueRules, segment_cues, separated
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.voices import VoiceLine


def cue_rules(settings: SubtitleSettings, variant: str) -> CueRules:
    chars = settings.short_max_chars_per_line if variant == SHORT else settings.max_chars_per_line
    return CueRules(
        max_chars=chars,
        max_lines=settings.max_lines,
        max_seconds=settings.max_cue_seconds,
        min_seconds=settings.min_cue_seconds,
    )


def timeline_cues(
    segments: Sequence[Segment], voices: Mapping[str, VoiceLine], rules: CueRules
) -> list[Cue]:
    cues: list[Cue] = []
    for segment in segments:
        line = voices.get(segment.key)
        if segment.narration is None or line is None:
            continue
        cues.extend(segment_cues(line.words, segment.narration_start, line.seconds, rules))
    return separated(cues, rules.min_seconds)
