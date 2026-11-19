from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from autotube.domain.video_look import (
    ScreenCorner,
    SubtitlePosition,
    Transition,
    VideoQuality,
    Watermark,
)
from autotube.pipelines.narrated_video.artifacts import VARIANTS
from autotube.pipelines.narrated_video.stages.logo_check import LogoMissingError, require_logo
from tests.fixtures.kids_data import StageRig, quick_settings, run_chain, smart_writer, stage_named
from tests.fixtures.kids_fakes import FakeProviders
from tests.fixtures.look_rig import look_composition, rendered_command, settings_with


def logo(folder: Path) -> Path:
    path = folder / "logo.png"
    Image.new("RGBA", (40, 20), (255, 0, 0, 128)).save(path)
    return path


def test_subtitle_look_reaches_the_style() -> None:
    look = {
        "position": "top",
        "bold": True,
        "shadow": 2,
        "outline_width": 1.5,
        "box_background": True,
        "box_color": "#112233",
        "box_opacity": 0.4,
    }
    style = look_composition(settings_with(subtitles=look)).subtitle_style
    assert (style.position, style.bold, style.shadow, style.outline_width) == (
        SubtitlePosition.TOP,
        True,
        2.0,
        1.5,
    )
    assert (style.box, style.box_color, style.box_opacity) == (True, "#112233", 0.4)


def test_karaoke_words_travel_only_when_karaoke_is_on() -> None:
    assert look_composition(settings_with()).subtitle_words == ()
    sung = look_composition(settings_with(subtitles={"karaoke": True}))
    assert sung.subtitle_style.karaoke and sung.subtitle_words
    assert sung.subtitle_words[0].word == "Hello"


def test_output_choices_reach_the_composition() -> None:
    settings = settings_with(
        episode={"transition": "fade_through_black", "video_quality": "best"},
        short={"fps": 24, "video_quality": "draft"},
    )
    episode, short = look_composition(settings), look_composition(settings, "short")
    assert (episode.transition, episode.quality, episode.fps) == (
        Transition.FADE_THROUGH_BLACK,
        VideoQuality.BEST,
        30,
    )
    assert (short.transition, short.quality, short.fps) == (
        Transition.FADE_THROUGH_BLACK,
        VideoQuality.DRAFT,
        24,
    )


def test_a_logo_is_placed_on_the_videos_it_is_switched_on_for(tmp_path: Path) -> None:
    visuals = {
        "logo_file": str(logo(tmp_path)),
        "logo_corner": "bottom_left",
        "logo_size_percent": 20,
        "logo_opacity": 0.5,
        "logo_margin_percent": 4,
        "logo_on_short": False,
    }
    settings = settings_with(visuals=visuals)
    assert look_composition(settings).watermark == Watermark(
        image=tmp_path / "logo.png",
        corner=ScreenCorner.BOTTOM_LEFT,
        width_share=0.2,
        opacity=0.5,
        margin_share=0.04,
    )
    assert look_composition(settings, "short").watermark is None
    command = rendered_command(settings)
    assert f"file:{tmp_path / 'logo.png'}" in command
    assert "colorchannelmixer=aa=0.500[logo]" in command[command.index("-filter_complex") + 1]


def test_no_logo_file_means_no_watermark() -> None:
    assert look_composition(settings_with(visuals={"logo_on_episode": True})).watermark is None


@pytest.mark.parametrize(("episode", "short"), [(False, True), (True, False)])
def test_the_logo_can_mark_only_one_video(tmp_path: Path, episode: bool, short: bool) -> None:
    visuals = {"logo_file": str(logo(tmp_path)), "logo_on_episode": episode, "logo_on_short": short}
    settings = settings_with(visuals=visuals)
    marked = [look_composition(settings, variant).watermark is not None for variant in VARIANTS]
    assert marked == [episode, short]


def test_only_the_logo_check_needs_the_file(tmp_path: Path) -> None:
    present = look_composition(settings_with(visuals={"logo_file": str(logo(tmp_path))}))
    gone = look_composition(settings_with(visuals={"logo_file": str(tmp_path / "gone.png")}))
    assert gone.watermark is not None and gone.watermark.image == tmp_path / "gone.png"
    require_logo(present)
    require_logo(look_composition(settings_with()))
    with pytest.raises(LogoMissingError, match=r"visuals\.logo_file: no picture at"):
        require_logo(gone)


def test_the_edit_stage_fails_on_a_missing_logo(tmp_path: Path) -> None:
    settings = quick_settings(visuals={"logo_file": str(tmp_path / "gone.png")})
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=smart_writer()))
    run_chain(rig, "music")
    with pytest.raises(LogoMissingError, match=r"visuals\.logo_file"):
        rig.run(stage_named("assemble"))
