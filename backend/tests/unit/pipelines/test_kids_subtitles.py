from __future__ import annotations

from automator.domain.capabilities import WordTiming
from automator.pipelines.kids_story.subtitles.cues import (
    Cue,
    CueRules,
    segment_cues,
    separated,
    word_groups,
    wrapped,
)
from automator.pipelines.kids_story.subtitles.srt import parse_srt, render_srt, timestamp
from automator.pipelines.kids_story.subtitles.timeline_cues import timeline_cues
from automator.pipelines.kids_story.text.graphemes import grapheme_length
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.voices import VoiceLine

RULES = CueRules(max_chars=20, max_lines=2, max_seconds=6.0, min_seconds=0.5)


def timed(text: str, step: float = 0.5) -> list[WordTiming]:
    return [
        WordTiming(word=word, start_seconds=index * step, end_seconds=index * step + step * 0.8)
        for index, word in enumerate(text.split())
    ]


def test_cues_break_at_sentences() -> None:
    groups = word_groups(timed("Kutty smiled. Mittu sang a song!"), RULES)
    assert [[word.word for word in group] for group in groups] == [
        ["Kutty", "smiled."],
        ["Mittu", "sang", "a", "song!"],
    ]


def test_cues_respect_line_length_and_line_count() -> None:
    text = "the little elephant walked slowly to the big mango tree in the morning sun"
    cues = segment_cues(timed(text), 0.0, 20.0, RULES)
    assert len(cues) > 1
    for cue in cues:
        assert len(cue.lines) <= RULES.max_lines
        assert all(grapheme_length(line) <= RULES.max_chars for line in cue.lines)
    assert " ".join(cue.text for cue in cues) == text


def test_tamil_lines_count_graphemes_not_code_points() -> None:
    text = "குட்டி யானை பெரிய மாமரத்தை நோக்கி நடந்தான்."
    lines = wrapped(text.split(), 12)
    assert all(grapheme_length(line) <= 12 for line in lines)
    assert " ".join(lines) == text
    assert len("மாமரத்தை") > grapheme_length("மாமரத்தை")


def test_long_tamil_word_is_split_between_clusters_only() -> None:
    lines = wrapped(["மகிழ்ச்சியுடன்"], 3)
    assert "".join(lines) == "மகிழ்ச்சியுடன்"
    assert all(line[0] not in "ாிீுூெேை்" for line in lines)


def test_cues_are_offset_and_kept_inside_the_audio() -> None:
    words = [WordTiming(word="late", start_seconds=0.2, end_seconds=9.0)]
    cues = segment_cues(words, 10.0, 2.0, RULES)
    assert cues[0].start == 10.2 and cues[0].end == 12.0


def test_separated_removes_overlaps_and_extends_short_cues() -> None:
    cues = [
        Cue(start=0.0, end=1.5, lines=("one",), limit=5.0),
        Cue(start=1.0, end=1.1, lines=("two",), limit=5.0),
        Cue(start=4.9, end=4.9, lines=("three",), limit=4.9),
    ]
    result = separated(cues, 0.5)
    assert [(cue.start, cue.end) for cue in result] == [(0.0, 1.0), (1.0, 1.5)]


def test_no_word_timings_means_no_guessed_cues() -> None:
    assert segment_cues([], 0.0, 3.0, RULES) == []


def test_timeline_cues_place_each_segment_at_its_narration_start() -> None:
    line = VoiceLine(
        segment="scene-0",
        filename="v.wav",
        seconds=1.0,
        text="Hi there.",
        words=tuple(timed("Hi there.")),
    )
    segments = [
        Segment(
            key="intro", visual_key="card", min_seconds=3, start=0, duration=3, narration_start=0.4
        ),
        Segment(
            key="scene-0",
            visual_key="s",
            narration="v.wav",
            narration_seconds=1.0,
            min_seconds=1,
            scene=0,
            start=3,
            duration=2,
            narration_start=3.4,
        ),
    ]
    cues = timeline_cues(segments, {"scene-0": line}, RULES)
    assert [(cue.start, cue.text) for cue in cues] == [(3.4, "Hi there.")]


def test_srt_round_trip() -> None:
    cues = [
        Cue(start=0.0, end=1.25, lines=("Hello,", "friends"), limit=9),
        Cue(start=3661.5, end=3662.0, lines=("வணக்கம்",), limit=4000),
    ]
    content = render_srt(cues)
    assert content.startswith(
        "1\n00:00:00,000 --> 00:00:01,250\nHello,\nfriends\n\n2\n01:01:01,500"
    )
    entries = parse_srt(content)
    assert [(entry.start, entry.end, entry.text) for entry in entries] == [
        (0.0, 1.25, "Hello, friends"),
        (3661.5, 3662.0, "வணக்கம்"),
    ]
    assert render_srt([]) == "" and parse_srt("garbage") == []
    assert timestamp(-1) == "00:00:00,000"
