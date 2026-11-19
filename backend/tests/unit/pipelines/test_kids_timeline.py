from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.narrated_video.settings.output import ShortSceneSelection, ShortSettings
from autotube.pipelines.narrated_video.timeline.composition import (
    Sources,
    composition,
    subtitle_style,
)
from autotube.pipelines.narrated_video.timeline.cuts import story_cuts
from autotube.pipelines.narrated_video.timeline.needs import clip_needs
from autotube.pipelines.narrated_video.timeline.plan import (
    Padding,
    SegmentSpec,
    fit_within,
    laid_out,
    total_seconds,
)
from autotube.pipelines.narrated_video.timeline.selection import short_scene_indexes
from autotube.pipelines.narrated_video.timeline.variants import planned
from tests.fixtures.fonts import embedded_font, embedded_font_family
from tests.fixtures.kids_data import quick_settings, story, voices

PADDING = Padding(lead_in=0.5, tail=1.0)


def test_laid_out_accumulates_padding_and_minimums() -> None:
    specs = [
        SegmentSpec(key="intro", visual_key="card", min_seconds=3.0),
        SegmentSpec(
            key="scene-0",
            visual_key="s0",
            narration="a.wav",
            narration_seconds=4.0,
            min_seconds=2.0,
            scene=0,
        ),
        SegmentSpec(
            key="scene-1",
            visual_key="s1",
            narration="b.wav",
            narration_seconds=0.2,
            min_seconds=2.5,
            scene=1,
        ),
    ]
    segments = laid_out(specs, PADDING)
    assert [(item.start, item.duration, item.narration_start) for item in segments] == [
        (0.0, 3.0, 0.5),
        (3.0, 5.5, 3.5),
        (8.5, 2.5, 9.0),
    ]
    assert total_seconds(segments) == 11.0 and total_seconds([]) == 0.0


def test_fit_within_skips_segments_that_do_not_fit() -> None:
    specs = [
        SegmentSpec(
            key=f"scene-{n}",
            visual_key="v",
            narration="x",
            narration_seconds=seconds,
            min_seconds=1,
            scene=n,
        )
        for n, seconds in enumerate([10.0, 30.0, 5.0])
    ]
    assert [spec.key for spec in fit_within(specs, PADDING, 20.0)] == ["scene-0", "scene-2"]


def test_short_scene_selection_modes() -> None:
    chosen = story(short_scenes=[8, 2, 2, 40, 0])
    assert short_scene_indexes(chosen, ShortSettings()) == [0, 2, 8]
    assert short_scene_indexes(chosen, ShortSettings(max_scenes=2)) == [0, 2]
    first = ShortSettings(scene_selection=ShortSceneSelection.FIRST_N, first_n_scenes=3)
    assert short_scene_indexes(chosen, first) == [0, 1, 2]
    heroes = story(short_scenes=[])
    assert short_scene_indexes(heroes, ShortSettings()) == [0, 6]


def test_episode_plan_has_cards_scenes_and_language_keys() -> None:
    settings = quick_settings()
    segments = planned(story(), voices(story()), settings, "episode")
    keys = [item.visual_key for item in segments]
    assert keys[0] == "card-intro-en@episode" and keys[-1] == "card-outro-en@episode"
    assert keys[1:-1] == [f"scene-{index}@episode" for index in range(9)]
    assert segments[1].duration == 10.0 + 0.4 + 0.8


def test_episode_without_cards_speaks_intro_over_the_first_scene() -> None:
    settings = quick_settings(episode={"intro_card": False, "outro_card": False})
    segments = planned(story(), voices(story()), settings, "episode")
    assert segments[0].key == "intro" and segments[0].visual_key == "scene-0@episode"
    without = {key: line for key, line in voices(story()).items() if key not in {"intro", "outro"}}
    assert [item.key for item in planned(story(), without, settings, "episode")][0] == "scene-0"


def test_short_plan_opens_with_hook_and_respects_max_duration() -> None:
    settings = quick_settings(short={"max_duration_seconds": 40})
    segments = planned(story(), voices(story()), settings, "short")
    assert segments[0].key == "hook" and segments[0].visual_key == "scene-0@short"
    assert total_seconds(segments) <= 40
    assert all(item.visual_key.endswith("@short") for item in segments)
    off = quick_settings(short={"enabled": False})
    assert planned(story(), voices(story()), off, "short") == []
    tiny = quick_settings(short={"max_duration_seconds": 10})
    assert planned(story(), voices(story(), seconds=20), tiny, "short") == []


def test_clip_needs_take_the_longest_use_of_each_visual() -> None:
    settings = quick_settings()
    english = story()
    tamil = story("ta")
    cuts = [
        *story_cuts(english, voices(english, 5.0), settings),
        *story_cuts(tamil, voices(tamil, 8.0), settings),
    ]
    needs = clip_needs(cuts)
    assert needs["scene-0@episode"].seconds == pytest.approx(8.0 + 1.2)
    short_need = needs["scene-0@short"]
    assert short_need.scene == 0 and short_need.variant == "short"
    tamil_short = next(cut for cut in cuts if cut.name == "ta-short")
    longest = max(
        item.duration for item in tamil_short.segments if item.visual_key == "scene-0@short"
    )
    assert short_need.seconds == pytest.approx(longest)
    for card in ("card-intro-ta", "card-intro-en", "card-outro-en", "card-outro-ta"):
        assert f"{card}@episode" in needs


def test_composition_carries_settings_and_offsets(tmp_path: Path) -> None:
    settings = quick_settings(
        subtitles={"burn_in_episode": True}, music={"volume": 0.3, "ducking": 0.9}
    )
    segments = planned(story(), voices(story()), settings, "episode")
    sources = Sources(
        workspace=tmp_path,
        clips={item.visual_key: tmp_path / "clip.mp4" for item in segments},
        voices=voices(story()),
        effects={"birds chirping": tmp_path / "birds.wav"},
        music=tmp_path / "music.wav",
        subtitles=tmp_path / "en.srt",
    )
    made = composition(segments, story(), sources, settings, "episode")
    assert (made.width, made.height) == (1280, 720)
    assert made.subtitle_style.burn_in and made.music_volume == 0.3 and made.music_ducking == 0.9
    assert made.narration[1].start_seconds == segments[1].narration_start
    assert made.sound_effects[0].start_seconds == segments[1].start + 0.3
    assert made.loudness_lufs == settings.episode.loudness_lufs


def test_subtitle_style_per_variant_and_language() -> None:
    settings = quick_settings()
    short = subtitle_style(settings, "ta", "short")
    assert short.burn_in and short.font_family == "Noto Sans Tamil" and short.font_size == 64
    episode = subtitle_style(settings, "en", "episode")
    assert not episode.burn_in and episode.font_family == "Noto Sans"
    assert (episode.margin_bottom, episode.margin_sides, episode.font_file) == (58, 51, None)
    assert short.margin_bottom == 282


def test_subtitle_style_names_the_font_file_it_found(tmp_path: Path) -> None:
    font = embedded_font(tmp_path)
    settings = quick_settings(subtitles={"font_files": {"en": [str(font)], "ta": []}})
    style = subtitle_style(settings, "en", "episode")
    assert (style.font_family, style.font_file) == (embedded_font_family(), font)
