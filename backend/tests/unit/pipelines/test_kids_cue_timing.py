from __future__ import annotations

import pytest

from autotube.domain.capabilities import WordTiming
from autotube.pipelines.narrated_video.subtitles.cues import Cue, CueRules, separated
from autotube.pipelines.narrated_video.subtitles.timing import (
    Window,
    durations,
    screenfuls,
    segment_cues,
)
from autotube.pipelines.narrated_video.text.graphemes import grapheme_length

RULES = CueRules(max_chars=20, max_lines=2, max_seconds=2.5, min_seconds=0.5)
SPLIT = CueRules(max_chars=6, max_lines=2, max_seconds=60, min_seconds=0)


def timed(text: str, step: float) -> list[WordTiming]:
    return [
        WordTiming(word=word, start_seconds=index * step, end_seconds=index * step + step * 0.8)
        for index, word in enumerate(text.split())
    ]


def word(text: str, start: float, end: float) -> list[WordTiming]:
    return [WordTiming(word=text, start_seconds=start, end_seconds=end)]


def spans(cues: list[Cue]) -> list[float]:
    return [moment for cue in cues for moment in (cue.start, cue.end)]


def test_cues_respect_line_length_and_line_count() -> None:
    text = "the little elephant walked slowly to the big mango tree in the morning sun"
    cues = segment_cues(timed(text, 0.5), 0.0, 20.0, RULES)
    assert len(cues) > 1
    for cue in cues:
        assert len(cue.lines) <= RULES.max_lines
        assert all(grapheme_length(line) <= RULES.max_chars for line in cue.lines)
    assert " ".join(cue.text for cue in cues) == text


def test_short_words_are_split_by_time_alone() -> None:
    cues = segment_cues(timed("a b c d e f g h", 0.4), 0.0, 10.0, RULES)
    assert len(cues) > 1 and all(cue.end - cue.start <= RULES.max_seconds for cue in cues)


def test_cues_are_offset_and_kept_inside_the_audio() -> None:
    [cue] = segment_cues(word("late", 0.2, 9.0), 10.0, 2.0, RULES)
    assert (cue.start, cue.end) == pytest.approx((10.2, 12.0))


def test_no_word_timings_means_no_guessed_cues() -> None:
    assert segment_cues([], 0.0, 3.0, RULES) == []


def test_overlapping_words_keep_their_order() -> None:
    words = [*word("one", 0.0, 1.0), *word("two.", 0.5, 1.2)]
    [cue] = segment_cues(words, 0.0, 2.0, RULES)
    assert cue.text == "one two." and cue.start <= cue.end


def test_a_zero_length_word_is_shown_for_the_shortest_cue() -> None:
    [cue] = separated(segment_cues(word("pop.", 1.0, 1.0), 0.0, 3.0, RULES), RULES.min_seconds)
    assert spans([cue]) == pytest.approx([1.0, 1.5])


def test_a_word_after_the_audio_still_shows_before_it_ends() -> None:
    cues = separated(segment_cues(word("late.", 5.0, 6.0), 0.0, 3.0, RULES), RULES.min_seconds)
    assert [cue.text for cue in cues] == ["late."]
    assert spans(cues) == pytest.approx([2.5, 3.0])


def test_a_cue_with_more_lines_than_allowed_becomes_consecutive_cues() -> None:
    cues = segment_cues(word("b" * 30, 0.0, 10.0), 0.0, 20.0, SPLIT)
    assert [len(cue.lines) for cue in cues] == [2, 2, 1]
    assert spans(cues) == pytest.approx([0.0, 4.0, 4.0, 8.0, 8.0, 10.0])


def test_one_line_screens_split_a_cue_line_by_line() -> None:
    rules = SPLIT.model_copy(update={"max_lines": 1})
    cues = segment_cues(word("b" * 18, 0.0, 3.0), 0.0, 3.0, rules)
    assert [cue.lines for cue in cues] == [("bbbbbb",)] * 3
    assert spans(cues) == pytest.approx([0.0, 1.0, 1.0, 2.0, 2.0, 3.0])


def test_split_screens_last_the_shortest_cue_using_the_free_time_after() -> None:
    rules = SPLIT.model_copy(update={"min_seconds": 1.0})
    cues = segment_cues([*word("b" * 30, 0.0, 1.0), *word("next", 5.0, 6.0)], 0.0, 9.0, rules)
    assert [cue.text for cue in cues][-1] == "next"
    assert all(cue.end - cue.start >= 1.0 - 1e-9 for cue in cues)
    assert "".join(cue.text.replace(" ", "") for cue in cues[:-1]) == "b" * 30


def test_screens_merge_rather_than_vanish_when_there_is_no_time() -> None:
    rules = SPLIT.model_copy(update={"min_seconds": 1.0})
    window = Window(start=0.0, end=1.5, room=1.5, limit=1.5)
    [cue] = screenfuls(window, ["aaaaaa", "bbbbbb", "cccccc"], rules)
    assert cue.lines == ("aaaaaa", "bbbbbb", "cccccc") and spans([cue]) == [0.0, 1.5]


def test_split_screens_cover_the_window_without_overlap() -> None:
    rules = SPLIT.model_copy(update={"min_seconds": 0.5})
    cues = segment_cues(word("c" * 40, 2.0, 9.0), 1.0, 10.0, rules)
    assert cues[0].start == pytest.approx(3.0) and cues[-1].end == pytest.approx(10.0)
    assert all(
        left.end == pytest.approx(right.start) for left, right in zip(cues, cues[1:], strict=False)
    )
    assert sum(cue.end - cue.start for cue in cues) == pytest.approx(7.0)


def test_durations_share_what_is_left_after_the_minimum() -> None:
    assert durations(10.0, [1, 3], 1.0) == pytest.approx([3.0, 7.0])
    assert durations(1.0, [1, 3], 1.0) == pytest.approx([0.5, 0.5])
    assert screenfuls(Window(start=0, end=1, room=1, limit=1), [], RULES) == []


def test_late_sentences_join_rather_than_vanish() -> None:
    words = [*word("one.", 9.0, 9.2), *word("two.", 9.4, 9.6), *word("three.", 9.7, 9.9)]
    cues = separated(segment_cues(words, 0.0, 9.5, RULES), RULES.min_seconds)
    assert " ".join(cue.text for cue in cues) == "one. two. three."
    assert all(left.end <= right.start for left, right in zip(cues, cues[1:], strict=False))


def test_screens_never_run_past_the_next_group() -> None:
    rules = SPLIT.model_copy(update={"min_seconds": 0.5})
    words = [*word("b" * 18, 0.0, 4.0), *word("next", 2.0, 3.0)]
    cues = segment_cues(words, 0.0, 9.0, rules)
    assert cues[-1].text == "next"
    assert all(cue.end <= cues[-1].start + 1e-9 for cue in cues[:-1])
