from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.capabilities import VideoComposition
from autotube.domain.video_look import ScreenCorner, Transition, VideoQuality, Watermark
from autotube.infrastructure.providers.media.composition_inputs import plan_inputs
from autotube.infrastructure.providers.media.composition_video import video_graph
from autotube.infrastructure.providers.media.encoder_quality import quality_crf
from autotube.infrastructure.providers.media.media_commands import compose_command
from autotube.infrastructure.providers.media.transitions import overlaps
from tests.unit.infrastructure.providers.media_fixtures import OPTIONS, clip, composition

BLENDED = (clip("a.png", 0, 2), clip("b.mp4", 1.5, 2))
LOGO = Watermark(image=Path("/w/logo.png"), width_share=0.12, opacity=0.8, margin_share=0.03)


def graph_of(made: VideoComposition) -> list[str]:
    return video_graph(made, plan_inputs(made), 3.5, OPTIONS)


def test_overlaps_are_read_from_the_timeline() -> None:
    assert overlaps(BLENDED) == [0.0, 0.5, 0.0]
    assert overlaps(composition().visuals) == [0.0, 0.0, 0.0]


def test_a_cut_never_fades_clips_even_when_they_overlap() -> None:
    graph = graph_of(composition(visuals=BLENDED))
    assert graph[3].endswith("setpts=PTS-STARTPTS+1.500/TB[v1]")
    assert graph[1].endswith("setpts=PTS-STARTPTS+0.000/TB[v0]")


def test_a_crossfade_fades_the_incoming_clip_over_the_outgoing_one() -> None:
    graph = graph_of(composition(visuals=BLENDED, transition=Transition.CROSSFADE))
    assert graph[1].endswith("setpts=PTS-STARTPTS+0.000/TB[v0]")
    assert graph[3].endswith(
        "setpts=PTS-STARTPTS+1.500/TB,format=yuva420p,fade=t=in:st=1.500:d=0.500:alpha=1[v1]"
    )


def test_fade_through_black_darkens_then_reveals() -> None:
    graph = graph_of(composition(visuals=BLENDED, transition=Transition.FADE_THROUGH_BLACK))
    assert graph[1].endswith("+0.000/TB,fade=t=out:st=1.500:d=0.250[v0]")
    assert graph[3].endswith("+1.500/TB,format=yuva420p,fade=t=in:st=1.750:d=0.250:alpha=1[v1]")


def test_a_watermark_is_scaled_faded_and_placed_before_the_subtitles() -> None:
    made = composition(watermark=LOGO)
    plan = plan_inputs(made)
    assert (plan.watermark, plan.args[-6:]) == (
        6,
        ["-f", "image2", "-pattern_type", "none", "-i", "file:/w/logo.png"],
    )
    graph = graph_of(made)
    assert "[6:v]scale=38:-2,format=rgba,colorchannelmixer=aa=0.800[logo]" in graph
    assert "[o1][logo]overlay=x=W-w-5:y=5[marked]" in graph
    assert graph[-1].startswith("[marked]ass=filename=")


@pytest.mark.parametrize(
    ("corner", "place"),
    [
        (ScreenCorner.TOP_LEFT, "x=5:y=5"),
        (ScreenCorner.BOTTOM_LEFT, "x=5:y=H-h-5"),
        (ScreenCorner.BOTTOM_RIGHT, "x=W-w-5:y=H-h-5"),
    ],
)
def test_the_watermark_corner_sets_its_place(corner: ScreenCorner, place: str) -> None:
    graph = graph_of(composition(watermark=LOGO.model_copy(update={"corner": corner})))
    assert f"[o1][logo]overlay={place}[marked]" in graph


def test_a_logo_path_is_read_literally_as_one_still_picture() -> None:
    odd = Path("/my logos/it's:%d brand.webp")
    plan = plan_inputs(composition(watermark=LOGO.model_copy(update={"image": odd})))
    assert plan.args[-6:] == [
        "-f",
        "image2",
        "-pattern_type",
        "none",
        "-i",
        "file:/my logos/it's:%d brand.webp",
    ]


def test_one_clip_has_no_transition_to_draw() -> None:
    single = BLENDED[:1]
    assert overlaps(single) == [0.0, 0.0]
    graph = graph_of(composition(visuals=single, transition=Transition.CROSSFADE))
    assert graph[1].endswith("setpts=PTS-STARTPTS+0.000/TB[v0]")
    assert not any("alpha=1" in chain for chain in graph)


def test_no_watermark_adds_no_input() -> None:
    assert plan_inputs(composition()).watermark is None


@pytest.mark.parametrize(
    ("quality", "crf"),
    [
        (VideoQuality.DRAFT, "28"),
        (VideoQuality.STANDARD, "20"),
        (VideoQuality.HIGH, "16"),
        (VideoQuality.BEST, "12"),
    ],
)
def test_named_quality_sets_the_encoder_crf(quality: VideoQuality, crf: str) -> None:
    command = compose_command(composition(quality=quality), OPTIONS, Path("/o.mp4"), None, False)
    assert command[command.index("-crf") + 1] == crf


def test_quality_stays_within_the_encoder_range() -> None:
    assert (quality_crf(50, VideoQuality.DRAFT), quality_crf(2, VideoQuality.BEST)) == (51, 0)
