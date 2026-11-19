from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.capabilities import WordTiming
from autotube.domain.srt import SrtEntry
from autotube.domain.video_look import SubtitleStyle
from autotube.infrastructure.providers.media.ass_document import ass_document
from autotube.pipelines.narrated_video.subtitles.cues import Cue, CueRules
from autotube.pipelines.narrated_video.subtitles.karaoke import (
    karaoke_words,
    split_word,
    with_words,
)
from autotube.pipelines.narrated_video.subtitles.timing import segment_cues
from tests.fixtures.kids_data import StageRig, quick_settings, run_chain
from tests.fixtures.kids_fakes import FakeProviders, FakeSpeech

TAMIL = "தும்பிக்கையை"
NARROW = CueRules(max_chars=3, max_lines=2, max_seconds=6, min_seconds=0)


def timing(word: str, start: float, end: float) -> WordTiming:
    return WordTiming(word=word, start_seconds=start, end_seconds=end)


def cue(start: float, end: float, *lines: str, words: tuple[WordTiming, ...] = ()) -> Cue:
    return Cue(start=start, end=end, lines=lines, limit=end, words=words)


def test_a_long_tamil_word_splits_into_pieces_sharing_its_time() -> None:
    parts = split_word(timing(TAMIL, 1.0, 2.0), 10.0, NARROW)
    assert len(parts) == 2 and "".join(part.word for part in parts) == TAMIL
    assert sum(part.end_seconds - part.start_seconds for part in parts) == pytest.approx(1.0)
    assert (parts[0].start_seconds, parts[0].end_seconds) == pytest.approx((11.0, 11.5))
    assert parts[1].start_seconds == pytest.approx(parts[0].end_seconds)
    assert parts[1].end_seconds == pytest.approx(12.0)


def test_split_pieces_reach_the_cues_that_show_them() -> None:
    cues = segment_cues([timing(TAMIL, 0.0, 1.0)], 5.0, 1.0, NARROW)
    shown = [token for item in cues for line in item.lines for token in line.split()]
    attached = [word.word for item in cues for word in item.words]
    assert len(shown) == 2 and attached == shown


def test_words_are_handed_to_cues_by_how_many_tokens_each_shows() -> None:
    pieces = [timing(name, index, index + 1) for index, name in enumerate(["a", "lo", "ng", "b"])]
    cues = with_words([cue(0, 2, "a lo"), cue(2, 4, "ng b")], pieces)
    assert [[word.word for word in item.words] for item in cues] == [["a", "lo"], ["ng", "b"]]


def test_a_word_clamped_out_of_its_cue_is_dropped() -> None:
    early = timing("early", 0.5, 1.2)
    late = timing("late", 2.5, 3.0)
    words = karaoke_words([cue(1.0, 2.0, "early late", words=(early, late))])
    assert words == (timing("early", 1.0, 1.2),)


def test_no_word_timings_leave_karaoke_subtitles_plain() -> None:
    entry = SrtEntry(start=0.0, end=1.0, lines=("Hello",))
    document = ass_document([entry], SubtitleStyle(karaoke=True), (320, 180), 3.0, ())
    assert "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Hello" in document
    assert "Dialogue: 1," not in document


def test_a_voice_without_word_timings_still_edits_with_karaoke_on(tmp_path: Path) -> None:
    settings = quick_settings(short={"enabled": False}, subtitles={"karaoke": True})
    providers = FakeProviders(speech=FakeSpeech(with_words=False))
    rig = StageRig(tmp_path, settings=settings, languages=("en",), providers=providers)
    run_chain(rig, "assemble")
    [made] = rig.providers.media.compositions.values()
    assert made.subtitle_style.karaoke and made.subtitle_words == ()
