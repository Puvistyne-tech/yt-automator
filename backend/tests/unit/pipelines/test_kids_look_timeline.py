from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.srt import SrtEntry, parse_srt
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.timeline.plan import Segment, total_seconds
from tests.fixtures.kids_data import story
from tests.fixtures.look_rig import (
    look_segments,
    look_srt,
    rendered_ass,
    settings_with,
    spoken_lines,
)

SHOWN = "{\\alpha&H00&}"


def crossfade(seconds: float = 0.5) -> KidsStorySettings:
    return settings_with(episode={"transition": "crossfade", "transition_seconds": seconds})


def owner(entry: SrtEntry, segments: list[Segment]) -> int:
    return next(index for index, item in enumerate(segments) if item.end > entry.start)


@pytest.mark.parametrize("transition", ["crossfade", "fade_through_black"])
def test_a_transition_shortens_the_timeline_by_each_overlap(transition: str) -> None:
    cut = look_segments(settings_with(), "episode")
    blended = look_segments(settings_with(episode={"transition": transition}), "episode")
    assert total_seconds(blended) == pytest.approx(total_seconds(cut) - 0.5 * (len(cut) - 1))
    assert [item.duration for item in blended] == [item.duration for item in cut]


def test_narration_and_cues_move_with_their_scene() -> None:
    cut = look_segments(settings_with(), "episode")
    blended = look_segments(crossfade(), "episode")
    for before, after in zip(cut, blended, strict=True):
        assert after.narration_start - after.start == pytest.approx(
            before.narration_start - before.start
        )
    cut_cues = parse_srt(look_srt(settings_with()))
    moved = parse_srt(look_srt(crossfade()))
    assert len(moved) == len(cut_cues)
    for plain, shifted in zip(cut_cues, moved, strict=True):
        shift = 0.5 * owner(plain, cut)
        assert (shifted.start, shifted.end) == pytest.approx(
            (plain.start - shift, plain.end - shift)
        )
        assert shifted.lines == plain.lines


def test_long_transitions_shrink_so_narrations_never_overlap() -> None:
    segments = look_segments(crossfade(3.0), "episode")
    lines = spoken_lines(story())
    spoken = [
        (item.narration_start, item.narration_start + lines[item.key].seconds)
        for item in segments
        if item.narration is not None
    ]
    for (_, end), (start, _) in zip(spoken, spoken[1:], strict=False):
        assert start >= end - 1e-9
    for before, after in zip(segments, segments[1:], strict=False):
        shared = before.end - after.start
        assert 0 < shared <= min(before.duration, after.duration) / 2 + 1e-9


@pytest.mark.parametrize("variant", ["episode", "short"])
def test_karaoke_highlights_every_spoken_word_once(variant: str, tmp_path: Path) -> None:
    settings = settings_with(subtitles={"karaoke": True, "burn_in_episode": True})
    segments = look_segments(settings, variant)
    lines = spoken_lines(story())
    words = sum(len(lines[item.key].words) for item in segments if item.narration is not None)
    assert rendered_ass(settings, tmp_path, variant).count(SHOWN) == words


def test_karaoke_survives_a_crossfade(tmp_path: Path) -> None:
    settings = settings_with(
        subtitles={"karaoke": True}, episode={"transition": "crossfade", "transition_seconds": 1}
    )
    document = rendered_ass(settings, tmp_path)
    plain = rendered_ass(settings_with(subtitles={"karaoke": True}), tmp_path)
    assert document.count(SHOWN) == plain.count(SHOWN) > 0
