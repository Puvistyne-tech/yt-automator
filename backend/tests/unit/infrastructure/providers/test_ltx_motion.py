from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.capabilities import Capability, MotionRequest
from autotube.domain.providers import ProviderChoice
from autotube.infrastructure.providers.catalog import LocalProviderCatalog
from autotube.infrastructure.providers.motion.ltx_mlx import LtxMotion
from autotube.infrastructure.providers.motion.ltx_options import LtxOptions
from autotube.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import (
    RecordingRunner,
    chain_config,
    host,
    local_catalog,
    make_context,
)

MAC_TOOLS = host(binaries=frozenset({"ltx-2-mlx", "depthflow", "ffmpeg"}))


def request(seconds: float) -> MotionRequest:
    return MotionRequest(
        image=Path("/in/still.png"),
        prompt="a fox waves",
        duration_seconds=seconds,
        width=1080,
        height=1920,
        fps=30,
    )


def write_last_argument(command: list[str]) -> None:
    Path(command[-1]).write_bytes(b"clip")


def adapter(tmp_path: Path, runner: RecordingRunner) -> LtxMotion:
    options = LtxOptions(model_dir=str(tmp_path))
    return LtxMotion(options, make_context(tmp_path, runner=runner, probe=MAC_TOOLS))


def test_animate_chains_segments_and_finishes_in_one_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = RecordingRunner(effect=write_last_argument)
    output = adapter(tmp_path, runner).animate(request(5.0), tmp_path / "clips" / "a.mp4")
    first, chain, second, finish = runner.commands
    assert [command[0] for command in runner.commands] == [
        "ltx-2-mlx",
        "ffmpeg",
        "ltx-2-mlx",
        "ffmpeg",
    ]
    assert first[first.index("--image") + 1] == "/in/still.png"
    assert first[first.index("-H") + 1 : first.index("-H") + 4] == ["704", "-W", "384"]
    assert chain[chain.index("-i") + 1] == first[-1]
    assert second[second.index("--image") + 1] == chain[-1]
    assert finish[finish.index("-t") + 1] == "5"
    assert Path(chain[-1]).parent.parent == output.parent
    assert runner.calls[0].env == {
        "HF_HOME": str(tmp_path / ".autotube" / "hf"),
        "HF_HUB_OFFLINE": "1",
    }
    assert runner.calls[0].timeout_seconds == 1200.0
    assert [call.env for call in runner.calls[1::2]] == [None, None]
    assert output.read_bytes() == b"clip"
    assert not Path(chain[-1]).parent.exists()


def test_animate_fails_when_nothing_was_written(tmp_path: Path) -> None:
    with pytest.raises(UpstreamFailure):
        adapter(tmp_path, RecordingRunner()).animate(request(2.0), tmp_path / "a.mp4")


def test_available_reports_missing_binary_then_missing_model(tmp_path: Path) -> None:
    bare = make_context(tmp_path)
    assert "ltx-2-mlx" in (LtxMotion(LtxOptions(model_dir=str(tmp_path)), bare).available() or "")
    tools = make_context(tmp_path, probe=MAC_TOOLS)
    missing = str(tmp_path / "nope")
    assert missing in (LtxMotion(LtxOptions(model_dir=missing), tools).available() or "")
    assert LtxMotion(LtxOptions(model_dir=str(tmp_path)), tools).available() is None


def test_available_expands_the_home_folder_in_the_model_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    tools = make_context(tmp_path, probe=MAC_TOOLS)
    default = tmp_path / ".autotube" / "models" / "reverie-studio__ltx-2.5-mlx-q4-distilled"
    assert str(default) in (LtxMotion(LtxOptions(), tools).available() or "")
    default.mkdir(parents=True)
    assert LtxMotion(LtxOptions(), tools).available() is None


def fails_on_ltx(command: list[str]) -> None:
    if command[0] == "ltx-2-mlx":
        raise UpstreamFailure("ltx-2-mlx exited with 1")


def test_motion_falls_back_to_depthflow_when_ltx_fails(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=fails_on_ltx)
    catalog = LocalProviderCatalog(make_context(tmp_path, runner=runner, probe=MAC_TOOLS))
    chain = chain_config(
        Capability.MOTION,
        ProviderChoice(provider_id="ltx_mlx", options={"model_dir": str(tmp_path)}),
        ProviderChoice(provider_id="depthflow"),
    )
    motion = catalog.resolver([chain]).resolve(Capability.MOTION)
    assert motion.provider_id == "ltx_mlx"
    motion.animate(request(2.0), tmp_path / "a.mp4")
    assert motion.provider_id == "depthflow"


def test_motion_without_ltx_tools_resolves_to_an_offline_fallback(tmp_path: Path) -> None:
    resolver = local_catalog(tmp_path).resolver([])
    assert resolver.resolve(Capability.MOTION).provider_id == "ffmpeg_pan_zoom"
    assert resolver.skipped[Capability.MOTION][0].startswith("ltx_mlx: ltx-2-mlx is not installed")
