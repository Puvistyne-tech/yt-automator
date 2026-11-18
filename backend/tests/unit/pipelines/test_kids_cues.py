from __future__ import annotations

import pytest

from automator.domain.capabilities import WordTiming
from automator.domain.srt import parse_srt
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings
from automator.pipelines.kids_story.story.words import ends_sentence
from automator.pipelines.kids_story.subtitles.cues import (
    Cue,
    CueRules,
    segment_cues,
    separated,
    word_groups,
)
from automator.pipelines.kids_story.subtitles.layout import subtitle_layout
from automator.pipelines.kids_story.subtitles.srt import render_srt
from automator.pipelines.kids_story.subtitles.timeline_cues import cue_rules, timeline_cues
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.voices import VoiceLine

RULES = CueRules(max_chars=20, max_lines=2, max_seconds=2.5, min_seconds=0.5)


def timed(text: str, step: float) -> list[WordTiming]:
    return [
        WordTiming(word=word, start_seconds=index * step, end_seconds=index * step + step * 0.8)
        for index, word in enumerate(text.split())
    ]


def words_in(groups: list[list[WordTiming]]) -> list[list[str]]:
    return [[word.word for word in group] for group in groups]


def test_cue_rules_use_the_line_length_and_line_count_of_each_variant() -> None:
    subtitles = SubtitleSettings(
        max_chars_per_line=40, short_max_chars_per_line=20, max_lines=3, short_max_lines=1
    )
    settings = KidsStorySettings(subtitles=subtitles)
    short = cue_rules(subtitles, subtitle_layout(settings, "en", "short"))
    episode = cue_rules(subtitles, subtitle_layout(settings, "en", "episode"))
    assert (short.max_chars, short.max_lines) == (20, 1)
    assert (episode.max_chars, episode.max_lines) == (40, 3)


def test_time_limit_splits_mid_sentence_and_a_sentence_end_still_closes_a_cue() -> None:
    groups = word_groups(timed("a b c d. e f", 1.0), RULES)
    assert words_in(groups) == [["a", "b"], ["c", "d."], ["e", "f"]]


def test_short_words_are_split_by_time_alone() -> None:
    cues = segment_cues(timed("a b c d e f g h", 0.4), 0.0, 10.0, RULES)
    assert len(cues) > 1 and all(cue.end - cue.start <= RULES.max_seconds for cue in cues)


@pytest.mark.parametrize("word", ['share!"', "friend.'", "done.)", "சரி।"])
def test_quoted_and_bracketed_sentence_ends_close_a_cue(word: str) -> None:
    assert ends_sentence(word)


@pytest.mark.parametrize("word", ["hello,", '"hi', "", "'"])
def test_other_words_do_not_end_a_sentence(word: str) -> None:
    assert not ends_sentence(word)


def test_zero_length_and_late_words() -> None:
    zero = [WordTiming(word="pop.", start_seconds=1.0, end_seconds=1.0)]
    [cue] = separated(segment_cues(zero, 0.0, 3.0, RULES), RULES.min_seconds)
    assert (cue.start, cue.end) == (1.0, 1.5)
    late = [WordTiming(word="late.", start_seconds=5.0, end_seconds=6.0)]
    clipped = segment_cues(late, 0.0, 3.0, RULES)
    assert clipped[0].start == clipped[0].end == 3.0
    assert separated(clipped, RULES.min_seconds) == []


def test_overlapping_words_keep_their_order() -> None:
    words = [
        WordTiming(word="one", start_seconds=0.0, end_seconds=1.0),
        WordTiming(word="two.", start_seconds=0.5, end_seconds=1.2),
    ]
    [cue] = segment_cues(words, 0.0, 2.0, RULES)
    assert cue.text == "one two." and cue.start <= cue.end


def test_separated_extends_short_cues_only_up_to_the_next_cue() -> None:
    cues = [
        Cue(start=0.0, end=0.1, lines=("one",), limit=9.0),
        Cue(start=0.3, end=0.4, lines=("two",), limit=9.0),
        Cue(start=2.0, end=2.1, lines=("three",), limit=9.0),
    ]
    result = separated(cues, 0.5)
    assert [(cue.start, cue.end) for cue in result] == [(0.0, 0.3), (0.3, 0.8), (2.0, 2.5)]


def test_segments_without_a_voice_line_have_no_cues() -> None:
    segment = Segment(
        key="scene-0",
        visual_key="s",
        narration="voice/en-scene-0.wav",
        narration_seconds=1.0,
        min_seconds=1,
        scene=0,
        start=0,
        duration=2,
        narration_start=0.4,
    )
    other = VoiceLine(segment="scene-1", filename="v.wav", seconds=1.0, text="Hi.")
    assert timeline_cues([segment], {"scene-1": other}, RULES) == []


def test_srt_edge_cases() -> None:
    empty = render_srt([Cue(start=0.0, end=1.0, lines=(), limit=2.0)])
    assert empty == "1\n00:00:00,000 --> 00:00:01,000\n\n"
    no_index = "00:00:01,000 --> 00:00:02,000\nகுட்டி\nயானை"
    [entry] = parse_srt(no_index)
    assert (entry.start, entry.end, entry.text) == (1.0, 2.0, "குட்டி யானை")
    assert parse_srt("") == []
