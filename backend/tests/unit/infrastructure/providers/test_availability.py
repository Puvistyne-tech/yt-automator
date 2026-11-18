from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from autotube.infrastructure.providers.host import HostProbe
from autotube.infrastructure.providers.registry import ALL_SPECS
from tests.unit.infrastructure.providers.fakes import (
    FFMPEG_ONLY,
    host,
    make_context,
    unreachable,
)

SPECS = {spec.provider_id: spec for spec in ALL_SPECS}
NOTHING = host()
MISSING_FFMPEG = "ffmpeg is not installed or not on PATH"


def availability(
    tmp_path: Path,
    provider_id: str,
    probe: HostProbe = NOTHING,
    handler: Callable[[httpx.Request], httpx.Response] = unreachable,
) -> str | None:
    context = make_context(tmp_path, probe=probe, handler=handler)
    reason: str | None = SPECS[provider_id].default(context).available()
    return reason


def add_track(tmp_path: Path) -> None:
    folder = tmp_path / "assets" / "music"
    folder.mkdir(parents=True)
    (folder / "calm.mp3").write_bytes(b"x")


def add_ace_step_venv(tmp_path: Path) -> None:
    python = tmp_path / "tools" / "ace-step" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("")


@pytest.mark.parametrize(
    ("provider_id", "probe", "reason"),
    [
        ("espeak", NOTHING, "espeak-ng is not installed or not on PATH"),
        ("kokoro", NOTHING, "Python package 'kokoro' is not installed (uv sync --extra tts)"),
        ("ffmpeg_pan_zoom", NOTHING, MISSING_FFMPEG),
        ("ffmpeg_pan_zoom", FFMPEG_ONLY, None),
        ("edge_tts", host(modules=frozenset({"edge_tts"})), MISSING_FFMPEG),
        ("library_music", NOTHING, MISSING_FFMPEG),
        ("offline_text", NOTHING, None),
        ("offline_image", NOTHING, None),
        ("offline_speech", NOTHING, None),
        ("synth_music", NOTHING, None),
    ],
)
def test_availability_reasons(
    tmp_path: Path, provider_id: str, probe: HostProbe, reason: str | None
) -> None:
    assert availability(tmp_path, provider_id, probe) == reason


@pytest.mark.parametrize(
    ("prepare", "provider_id"), [(add_track, "library_music"), (add_ace_step_venv, "ace_step")]
)
def test_music_with_its_files_still_needs_ffmpeg(
    tmp_path: Path, prepare: Callable[[Path], None], provider_id: str
) -> None:
    prepare(tmp_path)
    assert availability(tmp_path, provider_id) == MISSING_FFMPEG
    assert availability(tmp_path, provider_id, FFMPEG_ONLY) is None


@pytest.mark.parametrize(
    "response",
    [httpx.Response(200, text="not json"), httpx.Response(200, json=["gemma3:12b"])],
    ids=["invalid json", "not an object"],
)
def test_ollama_with_a_confused_server_is_not_running(
    tmp_path: Path, response: httpx.Response
) -> None:
    reason = availability(tmp_path, "ollama", handler=lambda _: response)
    assert reason == (
        "Ollama is not running at http://127.0.0.1:11434 (start it with `ollama serve`)"
    )
