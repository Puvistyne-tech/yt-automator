from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from autotube.domain.capabilities import ImageRequest
from autotube.infrastructure.providers.image.mflux import (
    MfluxImage,
    MfluxOptions,
    mflux_command,
    mflux_env,
)
from tests.unit.infrastructure.providers.fakes import RecordingRunner, host, make_context

KLEIN_DIR = str(Path("~/.autotube/models/black-forest-labs__FLUX.2-klein-4B").expanduser())
SCHNELL = MfluxOptions(model="schnell")
MAC = host(binaries=frozenset({"mflux-generate"}), system="Darwin", machine="arm64")
KLEIN_MAC = host(
    binaries=frozenset({"mflux-generate-flux2"}),
    paths=frozenset({KLEIN_DIR}),
    system="Darwin",
    machine="arm64",
)


def save_png(size: tuple[int, int]) -> Callable[[list[str]], None]:
    def effect(command: list[str]) -> None:
        Image.new("RGB", size, (10, 20, 30)).save(command[command.index("--output") + 1])

    return effect


def fox_request(reference: Path) -> ImageRequest:
    return ImageRequest(
        prompt="a fox", width=330, height=180, seed=7, reference_images=(reference,)
    )


def test_mflux_command_and_exact_resize(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=save_png((336, 192)))
    context = make_context(tmp_path, runner=runner, probe=MAC, secrets={"huggingface_token": "hf"})
    adapter = MfluxImage(SCHNELL.model_copy(update={"steps": 2}), context)
    reference = tmp_path / "ref.png"
    output = adapter.generate(fox_request(reference), tmp_path / "out.png")
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


def test_klein_command_uses_flux2_binary_and_expanded_local_folder(tmp_path: Path) -> None:
    reference = tmp_path / "ref.png"
    output = tmp_path / "out.png"
    command = mflux_command(fox_request(reference), MfluxOptions(), output)
    assert command == [
        "mflux-generate-flux2",
        "--model",
        KLEIN_DIR,
        "--prompt",
        "a fox",
        "--steps",
        "4",
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
    assert "--base-model" not in command


def test_klein_command_without_quantize_or_reference(tmp_path: Path) -> None:
    options = MfluxOptions(quantize=None, flux2_binary="flux2", model_dir="/packs/klein")
    request = ImageRequest(prompt="a fox", width=320, height=176, seed=1)
    command = mflux_command(request, options, tmp_path / "out.png")
    assert command[:3] == ["flux2", "--model", "/packs/klein"]
    assert "--quantize" not in command
    assert "--image-path" not in command


def test_klein_env_is_offline_and_keeps_token() -> None:
    assert mflux_env(MfluxOptions(), "hf") == {"HF_HUB_OFFLINE": "1", "HF_TOKEN": "hf"}
    assert mflux_env(MfluxOptions(), None) == {"HF_HUB_OFFLINE": "1"}
    assert mflux_env(SCHNELL, None) is None


def test_klein_generate_runs_offline(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=save_png((336, 192)))
    context = make_context(tmp_path, runner=runner, probe=KLEIN_MAC)
    MfluxImage(MfluxOptions(), context).generate(
        fox_request(tmp_path / "r.png"), tmp_path / "o.png"
    )
    assert runner.commands[0][0] == "mflux-generate-flux2"
    assert runner.calls[0].env == {"HF_HUB_OFFLINE": "1"}


def test_klein_is_the_default_and_saved_schnell_options_still_validate() -> None:
    assert MfluxOptions().model == "flux2-klein-4b"
    saved = MfluxOptions.model_validate({"model": "schnell", "steps": 4, "quantize": 8})
    assert saved.model == "schnell"


def test_mflux_needs_apple_silicon(tmp_path: Path) -> None:
    linux = make_context(tmp_path, probe=host(binaries=frozenset({"mflux-generate"})))
    assert "Apple-silicon" in (MfluxImage(SCHNELL, linux).available() or "")
    mac_without = make_context(tmp_path, probe=host(system="Darwin", machine="arm64"))
    assert "mflux-generate" in (MfluxImage(SCHNELL, mac_without).available() or "")
    assert MfluxImage(SCHNELL, make_context(tmp_path, probe=MAC)).available() is None


def test_klein_available_needs_flux2_binary_and_model_folder(tmp_path: Path) -> None:
    no_binary = host(paths=frozenset({KLEIN_DIR}), system="Darwin", machine="arm64")
    reason = MfluxImage(MfluxOptions(), make_context(tmp_path, probe=no_binary)).available()
    assert "mflux-generate-flux2" in (reason or "")
    no_folder = host(binaries=frozenset({"mflux-generate-flux2"}), system="Darwin", machine="arm64")
    reason = MfluxImage(MfluxOptions(), make_context(tmp_path, probe=no_folder)).available()
    assert reason == f"FLUX.2 klein model folder not found at {KLEIN_DIR}"
    ready = make_context(tmp_path, probe=KLEIN_MAC)
    assert MfluxImage(MfluxOptions(), ready).available() is None


def test_klein_on_linux_reports_apple_silicon_first(tmp_path: Path) -> None:
    linux = make_context(tmp_path, probe=host(binaries=frozenset({"mflux-generate-flux2"})))
    assert "Apple-silicon" in (MfluxImage(MfluxOptions(), linux).available() or "")
