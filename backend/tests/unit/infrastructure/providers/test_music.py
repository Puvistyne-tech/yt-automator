from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest

from automator.domain.capabilities import MusicRequest
from automator.infrastructure.providers.music.ace_step import AceStepMusic, AceStepOptions
from automator.infrastructure.providers.music.audio_fit import fade_filter
from automator.infrastructure.providers.music.library_music import (
    LibraryMusic,
    LibraryMusicOptions,
    pick_track,
)
from automator.infrastructure.providers.music.synth_music import SynthMusic, SynthMusicOptions
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import FFMPEG_ONLY, RecordingRunner, make_context


def read_samples(path: Path) -> tuple[int, int, np.ndarray]:
    with wave.open(str(path)) as handle:
        frames = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
        return handle.getframerate(), handle.getnchannels(), frames.reshape(-1, 2)


def test_synth_music_has_exact_length_stereo_and_fades(tmp_path: Path) -> None:
    adapter = SynthMusic(SynthMusicOptions(fade_seconds=0.5), make_context(tmp_path))
    path = adapter.compose(
        MusicRequest(prompt="sleepy owl", duration_seconds=2.5), tmp_path / "m.wav"
    )
    rate, channels, frames = read_samples(path)
    assert (rate, channels, len(frames)) == (44100, 2, 110250)
    assert np.abs(frames[:20]).max() < 200
    assert np.abs(frames[-20:]).max() < 200
    assert np.abs(frames).max() > 10000


def test_synth_music_is_deterministic_per_prompt(tmp_path: Path) -> None:
    adapter = SynthMusic(SynthMusicOptions(), make_context(tmp_path))
    one = adapter.compose(MusicRequest(prompt="a", duration_seconds=1), tmp_path / "1.wav")
    two = adapter.compose(MusicRequest(prompt="a", duration_seconds=1), tmp_path / "2.wav")
    three = adapter.compose(MusicRequest(prompt="b", duration_seconds=1), tmp_path / "3.wav")
    assert one.read_bytes() == two.read_bytes() != three.read_bytes()


def test_library_picks_matching_track_and_fits_it(tmp_path: Path) -> None:
    folder = tmp_path / "assets" / "music"
    folder.mkdir(parents=True)
    for name in ("happy-forest.mp3", "calm_night_lullaby.ogg", "notes.txt"):
        (folder / name).write_bytes(b"x")
    runner = RecordingRunner()
    adapter = LibraryMusic(
        LibraryMusicOptions(), make_context(tmp_path, runner=runner, probe=FFMPEG_ONLY)
    )
    assert adapter.available() is None
    adapter.compose(MusicRequest(prompt="A calm night", duration_seconds=10), tmp_path / "o.wav")
    assert runner.commands[0] == [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-stream_loop",
        "-1",
        "-i",
        str(folder / "calm_night_lullaby.ogg"),
        "-t",
        "10.000",
        "-af",
        "afade=t=in:st=0:d=1.500,afade=t=out:st=8.5:d=1.500",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(tmp_path / "o.wav"),
    ]


def test_library_without_tracks_is_unavailable(tmp_path: Path) -> None:
    adapter = LibraryMusic(LibraryMusicOptions(), make_context(tmp_path, probe=FFMPEG_ONLY))
    assert "add CC0 music tracks" in (adapter.available() or "")
    with pytest.raises(UpstreamFailure):
        adapter.compose(MusicRequest(prompt="x", duration_seconds=1), tmp_path / "o.wav")


def test_track_choice_is_stable_without_keyword_match(tmp_path: Path) -> None:
    tracks = [tmp_path / "a.mp3", tmp_path / "b.mp3", tmp_path / "c.mp3"]
    assert pick_track(tracks, "zzz") == pick_track(list(reversed(tracks)), "zzz")


def test_fade_is_clamped_to_half_the_duration() -> None:
    assert fade_filter(1.0, 3.0) == "afade=t=in:st=0:d=0.500,afade=t=out:st=0.5:d=0.500"
    assert fade_filter(1.0, 0.0) == "anull"


def test_ace_step_runs_in_its_own_python_then_fits(tmp_path: Path) -> None:
    python = tmp_path / "tools" / "ace-step" / "bin" / "python"
    runner = RecordingRunner()
    adapter = AceStepMusic(
        AceStepOptions(), make_context(tmp_path, runner=runner, probe=FFMPEG_ONLY)
    )
    assert "no ACE-Step venv" in (adapter.available() or "")
    python.parent.mkdir(parents=True)
    python.write_text("")
    assert adapter.available() is None
    output = adapter.compose(
        MusicRequest(prompt="lullaby", duration_seconds=30), tmp_path / "m.wav"
    )
    script_call, fit_call = runner.calls
    job = json.loads(script_call.stdin or "")
    assert script_call.command[:2] == [str(python), "-c"]
    assert job["audio_duration"] == 30
    assert job["save_path"] == str(tmp_path / "m.ace.wav")
    assert job["lyrics"] == "[instrumental]"
    assert fit_call.command[8] == str(tmp_path / "m.ace.wav")
    assert fit_call.command[-1] == str(output)
