from __future__ import annotations

import pytest

from automator.domain.capabilities import WordTiming
from automator.domain.srt import parse_srt
from automator.pipelines.kids_story.story.words import ends_sentence
from automator.pipelines.kids_story.subtitles.cues import (
    Cue,
    CueRules,
    separated,
    word_groups,
    wrapped,
)
from automator.pipelines.kids_story.subtitles.layout import subtitle_layout
from automator.pipelines.kids_story.subtitles.srt import render_srt, timestamp
from automator.pipelines.kids_story.subtitles.timeline_cues import cue_rules, timeline_cues
from automator.pipelines.kids_story.text.graphemes import grapheme_length
from automator.pipelines.kids_story.timeline.plan import Segment
from automator.pipelines.kids_story.timeline.voices import VoiceLine
from tests.fixtures.kids_data import quick_settings

RULES = CueRules(max_chars=20, max_lines=2, max_seconds=2.5, min_seconds=0.5)


def timed(text: str, step: float = 0.5) -> list[WordTiming]:
    return [
        WordTiming(word=word, start_seconds=index * step, end_seconds=index * step + step * 0.8)
        for index, word in enumerate(text.split())
    ]


def words_in(groups: list[list[WordTiming]]) -> list[list[str]]:
    return [[word.word for word in group] for group in groups]


def scene_segment(narration_start: float = 3.4) -> Segment:
    return Segment(
        key="scene-0",
        visual_key="s",
        narration="v.wav",
        narration_seconds=1.0,
        min_seconds=1,
        scene=0,
        start=3,
        duration=2,
        narration_start=narration_start,
    )


def test_cue_rules_use_the_line_length_and_line_count_of_each_variant() -> None:
    settings = quick_settings(
        subtitles={
            "max_chars_per_line": 40,
            "short_max_chars_per_line": 20,
            "max_lines": 3,
            "short_max_lines": 1,
        }
    )
    short = cue_rules(settings.subtitles, subtitle_layout(settings, "en", "short"))
    episode = cue_rules(settings.subtitles, subtitle_layout(settings, "en", "episode"))
    assert (short.max_chars, short.max_lines) == (20, 1)
    assert (episode.max_chars, episode.max_lines) == (40, 3)


def test_cues_break_at_sentences() -> None:
    groups = word_groups(timed("Kavin smiled. Mittu sang!"), RULES)
    assert words_in(groups) == [["Kavin", "smiled."], ["Mittu", "sang!"]]


def test_time_limit_splits_mid_sentence_and_a_sentence_end_still_closes_a_cue() -> None:
    groups = word_groups(timed("a b c d. e f", 1.0), RULES)
    assert words_in(groups) == [["a", "b"], ["c", "d."], ["e", "f"]]


@pytest.mark.parametrize("word", ['share!"', "friend.'", "done.)", "சரி।"])
def test_quoted_and_bracketed_sentence_ends_close_a_cue(word: str) -> None:
    assert ends_sentence(word)


@pytest.mark.parametrize("word", ["hello,", '"hi', "", "'"])
def test_other_words_do_not_end_a_sentence(word: str) -> None:
    assert not ends_sentence(word)


def test_tamil_lines_count_graphemes_not_code_points() -> None:
    text = "கவின் யானை பெரிய மாமரத்தை நோக்கி நடந்தான்."
    lines = wrapped(text.split(), RULES.model_copy(update={"max_chars": 12}))
    assert all(grapheme_length(line) <= 12 for line in lines)
    assert " ".join(lines) == text
    assert len("மாமரத்தை") > grapheme_length("மாமரத்தை")


def test_long_tamil_word_is_split_between_clusters_only() -> None:
    lines = wrapped(["மகிழ்ச்சியுடன்"], RULES.model_copy(update={"max_chars": 3}))
    assert "".join(lines) == "மகிழ்ச்சியுடன்"
    assert all(line[0] not in "ாிீுூெேை்" for line in lines)


def test_width_alone_splits_an_oversize_word() -> None:
    rules = RULES.model_copy(
        update={"max_chars": 100, "max_width": 100, "measure": lambda text: 10.0 * len(text)}
    )
    word = "x" * 30
    lines = wrapped([word], rules)
    assert "".join(lines) == word and all(10 * len(line) <= 100 for line in lines)


def test_a_cluster_wider_than_the_line_is_kept_on_its_own_line() -> None:
    rules = RULES.model_copy(update={"max_width": 5, "measure": lambda text: 10.0 * len(text)})
    assert wrapped(["ab"], rules) == ["a", "b"]


def test_separated_removes_overlaps_and_extends_short_cues() -> None:
    cues = [
        Cue(start=0.0, end=1.5, lines=("one",), limit=5.0),
        Cue(start=1.0, end=1.1, lines=("two",), limit=5.0),
        Cue(start=4.9, end=4.9, lines=("three",), limit=4.9),
    ]
    result = separated(cues, 0.5)
    assert [(cue.start, cue.end) for cue in result] == [(0.0, 1.0), (1.0, 1.5)]


def test_separated_extends_short_cues_only_up_to_the_next_cue() -> None:
    cues = [
        Cue(start=0.0, end=0.1, lines=("one",), limit=9.0),
        Cue(start=0.3, end=0.4, lines=("two",), limit=9.0),
        Cue(start=2.0, end=2.1, lines=("three",), limit=9.0),
    ]
    result = separated(cues, 0.5)
    assert [(cue.start, cue.end) for cue in result] == [(0.0, 0.3), (0.3, 0.8), (2.0, 2.5)]


def test_timeline_cues_place_each_segment_at_its_narration_start() -> None:
    line = VoiceLine(
        segment="scene-0",
        filename="v.wav",
        seconds=1.0,
        text="Hi there.",
        words=tuple(timed("Hi there.")),
    )
    intro = Segment(
        key="intro", visual_key="card", min_seconds=3, start=0, duration=3, narration_start=0.4
    )
    cues = timeline_cues([intro, scene_segment()], {"scene-0": line}, RULES)
    assert [(cue.start, cue.text) for cue in cues] == [(3.4, "Hi there.")]


def test_segments_without_a_voice_line_have_no_cues() -> None:
    other = VoiceLine(segment="scene-1", filename="v.wav", seconds=1.0, text="Hi.")
    assert timeline_cues([scene_segment(0.4)], {"scene-1": other}, RULES) == []


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
    assert [(entry.start, entry.end, entry.lines) for entry in entries] == [
        (0.0, 1.25, ("Hello,", "friends")),
        (3661.5, 3662.0, ("வணக்கம்",)),
    ]


def test_srt_rendering_edges() -> None:
    assert render_srt([]) == ""
    empty = render_srt([Cue(start=0.0, end=1.0, lines=(), limit=2.0)])
    assert empty == "1\n00:00:00,000 --> 00:00:01,000\n\n"
    assert timestamp(-1.0) == "00:00:00,000"
