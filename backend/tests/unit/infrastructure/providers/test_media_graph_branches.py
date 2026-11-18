from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from automator.domain.capabilities import SubtitleStyle
from automator.infrastructure.providers.media.composition_audio import audio_graph
from automator.infrastructure.providers.media.composition_inputs import plan_inputs
from automator.infrastructure.providers.media.composition_video import video_graph
from automator.infrastructure.providers.media.ffmpeg_options import FfmpegOptions
from automator.infrastructure.providers.media.subtitle_filter import subtitle_filter
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.media_fixtures import OPTIONS, clip, composition

MIX = ":duration=longest:normalize=0[mix]"


def audio_of(**changes: object) -> list[str]:
    built = composition(**changes)
    return audio_graph(built, plan_inputs(built), 3.5, OPTIONS, None)


def video_of(options: FfmpegOptions = OPTIONS, **changes: object) -> list[str]:
    built = composition(**changes)
    return video_graph(built, plan_inputs(built), 3.5, options)


@pytest.mark.parametrize(
    ("changes", "mix"),
    [
        ({"music": None}, "[voice][e0]amix=inputs=2"),
        ({"music": None, "sound_effects": ()}, "[voice]amix=inputs=1"),
        ({"narration": (), "sound_effects": (), "music_ducking": 0.5}, "[music]amix=inputs=1"),
        ({"narration": (), "music": None}, "[e0]amix=inputs=1"),
    ],
    ids=["narration and effects", "narration only", "music only", "effects only"],
)
def test_audio_stems_for_each_source_combination(changes: dict[str, object], mix: str) -> None:
    graph = audio_of(**changes)
    assert graph[-2] == f"{mix}{MIX}"
    assert not any("asplit" in chain for chain in graph)


@pytest.mark.parametrize(
    ("fade_seconds", "expected"),
    [(0.0, []), (10.0, ["afade=t=in:st=0:d=1.750", "afade=t=out:st=1.750:d=1.750"])],
)
def test_audio_fades_are_skipped_or_clamped(fade_seconds: float, expected: list[str]) -> None:
    steps = audio_of(fade_seconds=fade_seconds)[-1].split(",")
    assert [step.removesuffix("[aout]") for step in steps if "afade" in step] == expected


def test_burn_in_without_subtitles_only_formats() -> None:
    graph = video_of(subtitles=None, fade_seconds=0)
    assert graph[-1] == "[o1]format=yuv420p[vout]"


def test_video_fade_is_clamped_to_half_the_timeline() -> None:
    assert video_of(fade_seconds=10)[-1].endswith(
        "fade=t=in:st=0:d=1.750,fade=t=out:st=1.750:d=1.750,format=yuv420p[vout]"
    )


def test_single_visual_overlays_once() -> None:
    graph = video_of(visuals=(clip("only.jpg", 0, 3.5),), fade_seconds=0, subtitles=None)
    assert len(graph) == 4
    assert graph[2] == "[base][v0]overlay=eof_action=pass:repeatlast=0[o0]"
    assert graph[3] == "[o0]format=yuv420p[vout]"


@pytest.mark.parametrize("name", ["X.PNG", "scene.webp", "photo.JPEG", "old.bmp"])
def test_still_images_of_any_case_are_looped(name: str) -> None:
    plan = plan_inputs(composition(visuals=(clip(name, 0, 1),)))
    assert plan.args[:2] == ["-loop", "1"]


@pytest.mark.parametrize(
    ("width", "height", "size"), [(321, 181, "320x180"), (1, 3, "2x2"), (320, 180, "320x180")]
)
def test_frame_sizes_are_rounded_down_to_even(width: int, height: int, size: str) -> None:
    graph = video_of(width=width, height=height)
    scale = size.replace("x", ":")
    assert graph[0].startswith(f"color=c=#000000:s={size}:")
    assert graph[1].split(",")[:2] == [
        f"[0:v]scale={scale}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={scale}",
    ]


@pytest.mark.parametrize(("width", "height"), [(320, 180), (321, 181)])
def test_burned_subtitles_scale_with_the_even_height(width: int, height: int) -> None:
    assert "FontSize=57.6" in video_of(width=width, height=height)[-1]


def test_background_colour_is_configurable_and_validated() -> None:
    options = FfmpegOptions(background_color="#112233")
    assert video_of(options)[0].startswith("color=c=#112233:")
    with pytest.raises(ValidationError):
        FfmpegOptions(background_color="black:s=1x1")


@pytest.mark.parametrize("family", ["Kid's Font", "Comic Sans, MS", "A:B", "", "x[y]"])
def test_unsafe_font_names_are_refused(family: str) -> None:
    with pytest.raises(UpstreamFailure, match="may only use letters, digits"):
        subtitle_filter(Path("/w/s.srt"), SubtitleStyle(font_family=family), 1080, 3, "")


def test_safe_font_names_pass_through() -> None:
    style = SubtitleStyle(font_family="Noto Sans Tamil-Bold_2")
    rendered = subtitle_filter(Path("/w/s.srt"), style, 1080, 3, "")
    assert "FontName=Noto Sans Tamil-Bold_2," in rendered
