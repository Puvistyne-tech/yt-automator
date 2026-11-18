from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from automator.domain.capabilities import CameraMove, ImageRequest, MotionRequest
from automator.infrastructure.providers.image.mflux import MfluxImage, MfluxOptions
from automator.infrastructure.providers.image.offline_image import OfflineImage, OfflineImageOptions
from automator.infrastructure.providers.motion.depthflow import DepthflowMotion, DepthflowOptions
from automator.infrastructure.providers.motion.ffmpeg_pan_zoom import FfmpegPanZoom, PanZoomOptions
from automator.infrastructure.providers.motion.pan_zoom_filter import (
    PanZoomTuning,
    camera_expressions,
    pan_zoom_filter,
)
from tests.unit.infrastructure.providers.fakes import RecordingRunner, host, make_context

MAC = host(binaries=frozenset({"mflux-generate"}), system="Darwin", machine="arm64")


def save_png(size: tuple[int, int]) -> Callable[[list[str]], None]:
    def effect(command: list[str]) -> None:
        Image.new("RGB", size, (10, 20, 30)).save(command[command.index("--output") + 1])

    return effect


def test_mflux_command_and_exact_resize(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=save_png((336, 192)))
    context = make_context(tmp_path, runner=runner, probe=MAC, secrets={"huggingface_token": "hf"})
    adapter = MfluxImage(MfluxOptions(steps=2), context)
    reference = tmp_path / "ref.png"
    request = ImageRequest(
        prompt="a fox", width=330, height=180, seed=7, reference_images=(reference,)
    )
    output = adapter.generate(request, tmp_path / "out.png")
    assert runner.commands[0] == [
        "mflux-generate",
        "--model",
        "schnell",
        "--prompt",
        "a fox",
        "--steps",
        "2",
        "--seed",
        "7",
        "--width",
        "336",
        "--height",
        "192",
        "--output",
        str(output),
        "--quantize",
        "8",
        "--image-path",
        str(reference),
        "--image-strength",
        "0.4",
    ]
    assert runner.calls[0].env == {"HF_TOKEN": "hf"}
    with Image.open(output) as image:
        assert image.size == (330, 180)


def test_mflux_needs_apple_silicon(tmp_path: Path) -> None:
    linux = make_context(tmp_path, probe=host(binaries=frozenset({"mflux-generate"})))
    assert "Apple-silicon" in (MfluxImage(MfluxOptions(), linux).available() or "")
    mac_without = make_context(tmp_path, probe=host(system="Darwin", machine="arm64"))
    assert "mflux-generate" in (MfluxImage(MfluxOptions(), mac_without).available() or "")
    assert MfluxImage(MfluxOptions(), make_context(tmp_path, probe=MAC)).available() is None


def test_offline_image_is_sized_deterministic_and_prompt_dependent(tmp_path: Path) -> None:
    adapter = OfflineImage(OfflineImageOptions(), make_context(tmp_path))
    request = ImageRequest(prompt="a calm lake at sunset", width=96, height=54, seed=1)
    first = adapter.generate(request, tmp_path / "a.png")
    second = adapter.generate(request, tmp_path / "b.png")
    other = adapter.generate(request.model_copy(update={"seed": 2}), tmp_path / "c.png")
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() != other.read_bytes()
    with Image.open(first) as image:
        assert image.size == (96, 54)
        assert len(image.convert("RGB").getcolors(maxcolors=100000) or []) > 50


def motion(camera: CameraMove = CameraMove.PUSH_IN, intensity: float = 0.5) -> MotionRequest:
    return MotionRequest(
        image=Path("/in/still.png"),
        duration_seconds=2,
        width=320,
        height=180,
        fps=25,
        camera=camera,
        intensity=intensity,
    )


def test_pan_zoom_filter_supersamples_and_eases() -> None:
    tuning = PanZoomTuning(max_zoom=0.4, supersample=4, crf=18, preset="fast")
    assert pan_zoom_filter(motion(), tuning) == (
        "scale=1280:720:force_original_aspect_ratio=increase:flags=lanczos,crop=1280:720,"
        "zoompan=z='1+0.2000*((on/49)*(on/49)*(3-2*(on/49)))'"
        ":x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=50:s=320x180:fps=25,format=yuv420p"
    )


def test_every_camera_move_has_distinct_expressions() -> None:
    expressions = {camera_expressions(camera, 0.3, "E") for camera in CameraMove}
    assert len(expressions) == len(CameraMove)
    assert camera_expressions(CameraMove.STILL, 0.3, "E")[0] == "1"
    assert camera_expressions(CameraMove.PAN_LEFT, 0.3, "E")[1] == "(iw-iw/zoom)*(1-E)"


def test_pan_zoom_command(tmp_path: Path) -> None:
    runner = RecordingRunner()
    context = make_context(tmp_path, runner=runner, probe=host(binaries=frozenset({"ffmpeg"})))
    adapter = FfmpegPanZoom(PanZoomOptions(), context)
    output = adapter.animate(motion(), tmp_path / "clip.mp4")
    command = runner.commands[0]
    assert adapter.available() is None
    assert command[:7] == [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "/in/still.png",
    ]
    assert command[command.index("-frames:v") + 1] == "50"
    assert command[-1] == str(output)


def test_depthflow_maps_camera_and_intensity(tmp_path: Path) -> None:
    runner = RecordingRunner()
    adapter = DepthflowMotion(DepthflowOptions(), make_context(tmp_path, runner=runner))
    adapter.animate(motion(CameraMove.PULL_OUT, 0.5), tmp_path / "d.mp4")
    adapter.animate(motion(CameraMove.STILL), tmp_path / "s.mp4")
    assert runner.commands[0] == [
        "depthflow",
        "input",
        "-i",
        "/in/still.png",
        "dolly",
        "--reverse",
        "--intensity",
        "0.7",
        "main",
        "-o",
        str(tmp_path / "d.mp4"),
        "-w",
        "320",
        "-h",
        "180",
        "-f",
        "25",
        "-t",
        "2",
        "--ssaa",
        "1.5",
        "--quality",
        "50",
    ]
    assert runner.commands[1][4] == "main"
    assert "depthflow" in (adapter.available() or "")
