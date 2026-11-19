from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from autotube.domain.capabilities import MotionRequest
from autotube.infrastructure.providers.ffmpeg_args import x264_args
from autotube.infrastructure.providers.home_path import home_expanded
from autotube.infrastructure.providers.motion.ltx_options import LtxOptions
from autotube.infrastructure.providers.motion.ltx_plan import (
    finish_command,
    generation_size,
    last_frame_command,
    ltx_command,
    ltx_env,
    ltx_frame_count,
    segment_durations,
    segment_plan,
)

WORK = Path("/w")


def request(seconds: float = 2.0, width: int = 1280, height: int = 720) -> MotionRequest:
    return MotionRequest(
        image=Path("/in/still.png"),
        prompt="a fox waves",
        duration_seconds=seconds,
        width=width,
        height=height,
        fps=30,
    )


@pytest.mark.parametrize(
    ("total", "longest", "expected"),
    [(2.0, 3.0, [2.0]), (3.0, 3.0, [3.0]), (7.5, 3.0, [2.5, 2.5, 2.5]), (1e-9, 3.0, [1e-9])],
)
def test_segment_durations_split_evenly_within_the_longest(
    total: float, longest: float, expected: list[float]
) -> None:
    assert segment_durations(total, longest) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("seconds", "rate", "expected"),
    [(2.0, 24, 49), (3.0, 24, 73), (2.5, 24, 65), (0.01, 24, 9), (2.0, 25, 57)],
)
def test_ltx_frame_count_is_the_smallest_eight_k_plus_one(
    seconds: float, rate: int, expected: int
) -> None:
    assert ltx_frame_count(seconds, rate) == expected


def test_generation_size_picks_portrait_only_when_taller() -> None:
    options = LtxOptions()
    assert generation_size(request(), options) == (704, 384)
    assert generation_size(request(width=720, height=1280), options) == (384, 704)
    assert generation_size(request(width=720, height=720), options) == (704, 384)


@pytest.mark.parametrize("field", ["landscape_width", "portrait_height"])
def test_sizes_must_be_multiples_of_64(field: str) -> None:
    with pytest.raises(ValidationError):
        LtxOptions.model_validate({field: 700})


def test_segment_plan_chains_each_segment_from_the_previous_last_frame() -> None:
    plan = segment_plan(request(seconds=5.0), LtxOptions(), WORK)
    assert [(item.image, item.frames, item.output) for item in plan] == [
        (Path("/in/still.png"), 65, WORK / "segment-0.mp4"),
        (WORK / "start-1.png", 65, WORK / "segment-1.mp4"),
    ]


def test_ltx_command_matches_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/kid")
    item = segment_plan(request(), LtxOptions(), WORK)[0]
    assert ltx_command(request(), LtxOptions(), item) == [
        "ltx-2-mlx",
        "generate",
        "--distilled",
        "--model",
        "/home/kid/.autotube/models/reverie-studio__ltx-2.5-mlx-q4-distilled",
        "--prompt",
        "a fox waves",
        "--nag",
        "--negative-prompt",
        "text, captions, watermark, blurry, distorted, extra limbs",
        "--image",
        "/in/still.png",
        "0",
        "1.0",
        "-H",
        "384",
        "-W",
        "704",
        "-f",
        "49",
        "--frame-rate",
        "24",
        "--seed",
        "42",
        "--no-audio",
        "-o",
        "/w/segment-0.mp4",
    ]


def test_ltx_command_adds_text_encoder_and_drops_nag_and_distilled_when_asked() -> None:
    options = LtxOptions(
        model_dir="/packs/q8",
        text_encoder="mlx-community/gemma-3-12b-it-4bit",
        use_nag=False,
        distilled=False,
    )
    command = ltx_command(request(), options, segment_plan(request(), options, WORK)[0])
    assert command[1:4] == ["generate", "--model", options.model_dir]
    assert command[4:6] == ["--gemma", "mlx-community/gemma-3-12b-it-4bit"]
    assert {"--nag", "--negative-prompt"}.isdisjoint(command)


@pytest.mark.parametrize(("given", "sent"), [("3D", "3D"), ("", LtxOptions().negative_prompt)])
def test_request_negative_wins_else_option(given: str, sent: str) -> None:
    motion = request().model_copy(update={"negative_prompt": given})
    command = ltx_command(motion, LtxOptions(), segment_plan(motion, LtxOptions(), WORK)[0])
    assert command[command.index("--negative-prompt") + 1] == sent


def test_ltx_env_sets_offline_cache_only_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/home/kid")
    assert ltx_env(LtxOptions()) == {
        "HF_HOME": "/home/kid/.autotube/hf",
        "HF_HUB_OFFLINE": "1",
    }
    assert ltx_env(LtxOptions(hf_home="", hf_offline=False)) == {}


def test_last_frame_command_seeks_from_the_end() -> None:
    assert last_frame_command("ffmpeg", WORK / "a.mp4", WORK / "b.png") == [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-sseof",
        "-0.05",
        "-i",
        "/w/a.mp4",
        "-frames:v",
        "1",
        "/w/b.png",
    ]


def test_finish_command_joins_trims_scales_and_converts_rate() -> None:
    clips = [WORK / "segment-0.mp4", WORK / "segment-1.mp4"]
    odd = request(seconds=4.5, width=1281, height=721)
    command = finish_command(odd, LtxOptions(), clips, WORK / "out.mp4")
    assert command[5:9] == ["-i", "/w/segment-0.mp4", "-i", "/w/segment-1.mp4"]
    assert command[command.index("-filter_complex") + 1] == (
        "[0:v][1:v]concat=n=2:v=1:a=0,"
        "scale=1280:720:force_original_aspect_ratio=increase:flags=lanczos,"
        "crop=1280:720,setsar=1,fps=30,format=yuv420p"
    )
    assert command[command.index("-t") + 1] == "4.5"
    assert command[command.index("-r") + 1] == "30"
    assert command[-6:-1] == ["-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"]
    assert command[-1] == "/w/out.mp4"


def test_finish_command_holds_frames_for_a_lower_held_rate() -> None:
    held = request().model_copy(update={"held_frame_rate": 12})
    graph = finish_command(held, LtxOptions(), [WORK / "a.mp4"], WORK / "o.mp4")
    assert graph[graph.index("-filter_complex") + 1].endswith(
        "setsar=1,fps=30,fps=12,fps=30,format=yuv420p"
    )


def test_x264_args_encode_with_preset_crf_and_420_chroma() -> None:
    assert x264_args("fast", 18) == [
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
    ]


def test_home_expanded_resolves_tilde_and_keeps_absolute_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", "/home/kid")
    assert home_expanded("~/.autotube/hf") == "/home/kid/.autotube/hf"
    assert home_expanded("/packs/q8") == "/packs/q8"
