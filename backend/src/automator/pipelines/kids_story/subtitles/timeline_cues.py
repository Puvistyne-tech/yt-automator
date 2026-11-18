from __future__ import annotations

from collections.abc import Mapping, Sequence

from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings
from automator.pipelines.kids_story.subtitles.cues import Cue, CueRules, separated
from automator.pipelines.kids_story.subtitles.layout import SubtitleLayout
from automator.pipelines.kids_story.subtitles.timing import segment_cues
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.voices import VoiceLine


def cue_rules(settings: SubtitleSettings, layout: SubtitleLayout) -> CueRules:
    return CueRules(
        max_chars=layout.max_chars,
        max_lines=layout.max_lines,
        max_seconds=settings.max_cue_seconds,
        min_seconds=settings.min_cue_seconds,
        max_width=layout.line_width,
        measure=layout.font.measure,
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
