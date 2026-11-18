from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.capabilities import WordTiming
from automator.infrastructure.providers.tts.voice_language import lookup_language
from automator.infrastructure.providers.tts.whisper_aligner import AlignmentOptions, WhisperAligner
from automator.infrastructure.providers.tts.word_alignment import align_words
from automator.infrastructure.providers.tts.word_timing import estimate_timings
from tests.unit.infrastructure.providers.fakes import host


def timed(word: str, start: float, end: float) -> WordTiming:
    return WordTiming(word=word, start_seconds=start, end_seconds=end)


def test_estimates_are_proportional_to_word_length_and_ordered() -> None:
    timings = estimate_timings(["a", "elephant"], 0.0, 1.1)
    assert timings[0].end_seconds - timings[0].start_seconds == pytest.approx(0.1)
    assert timings[1].end_seconds - timings[1].start_seconds == pytest.approx(0.8)
    assert timings[1].start_seconds == pytest.approx(0.2)
    assert estimate_timings([], 0, 1) == ()
    assert estimate_timings(["x"], 1, 1) == ()


def test_alignment_keeps_original_words_and_fills_gaps() -> None:
    recognised = [timed("once", 0.1, 0.4), timed("a", 0.9, 1.0), timed("time", 1.0, 1.4)]
    aligned = align_words(["Once", "upon", "a", "time."], recognised, 2.0, 0.5)
    assert aligned is not None
    assert [word.word for word in aligned] == ["Once", "upon", "a", "time."]
    assert aligned[1].start_seconds >= 0.4
    assert aligned[1].end_seconds <= 0.9
    assert aligned[3] == timed("time.", 1.0, 1.4)


def test_alignment_rejects_poor_matches() -> None:
    assert align_words(["one", "two"], [timed("zebra", 0, 1)], 1.0, 0.5) is None
    assert align_words(["one"], [], 1.0, 0.5) is None


def test_trailing_unmatched_words_run_to_the_end() -> None:
    aligned = align_words(["hi", "there"], [timed("hi", 0.0, 0.3)], 1.0, 0.5)
    assert aligned is not None
    assert aligned[1].start_seconds == pytest.approx(0.3)
    assert aligned[1].end_seconds <= 1.0


def test_whisper_aligner_skips_cleanly_without_packages(tmp_path: Path) -> None:
    aligner = WhisperAligner(host(), AlignmentOptions())
    assert aligner.recognise(tmp_path / "a.wav", "en") is None


def test_whisper_aligner_returns_none_when_the_model_fails(tmp_path: Path) -> None:
    aligner = WhisperAligner(host(modules=frozenset({"faster_whisper"})), AlignmentOptions())
    assert aligner.recognise(tmp_path / "missing.wav", "ta-IN") is None


def test_language_lookup_falls_back_to_primary_subtag() -> None:
    voices = {"en": "a", "en-GB": "b"}
    assert lookup_language(voices, "en_gb") == "b"
    assert lookup_language(voices, "en-IN") == "a"
    assert lookup_language(voices, "ta") is None
