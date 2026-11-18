from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from automator.domain.capabilities import Capability, TimedClip, VideoComposition
from automator.infrastructure.providers.catalog import build_provider_catalog
from automator.infrastructure.providers.wav_io import write_wav
from tests.fixtures.fake_runtime import InMemorySecrets

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
        reason="ffmpeg and ffprobe are needed to render",
    ),
]
RATE = 16000
MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?[\d.]+|-inf) dB")


def tone(path: Path, seconds: float, pitch: float) -> Path:
    clock = np.arange(round(seconds * RATE)) / RATE
    return write_wav(path, 0.5 * np.sin(2 * np.pi * pitch * clock), RATE)


def mean_volume_after(video: Path, start: float) -> float:
    command = ["ffmpeg", "-hide_banner", "-ss", f"{start}", "-i", str(video)]
    command += ["-af", "volumedetect", "-vn", "-f", "null", "-"]
    stderr = subprocess.run(command, capture_output=True, text=True, check=True).stderr
    found = MEAN_VOLUME.findall(stderr)
    return float(found[-1]) if found else -np.inf


def still_image(tmp_path: Path) -> Path:
    still = tmp_path / "still.png"
    Image.new("RGB", (64, 36), (40, 80, 120)).save(still)
    return still


def compose(tmp_path: Path, composition: VideoComposition) -> Path:
    resolver = build_provider_catalog(InMemorySecrets(), tmp_path).resolver([])
    return resolver.resolve(Capability.MEDIA).compose_video(composition, tmp_path / "out.mp4")


def test_ducked_music_keeps_playing_after_the_narration_ends(tmp_path: Path) -> None:
    still = still_image(tmp_path)
    composition = VideoComposition(
        width=64,
        height=36,
        fps=10,
        visuals=(TimedClip(path=still, start_seconds=0, duration_seconds=4),),
        narration=(
            TimedClip(path=tone(tmp_path / "n.wav", 1, 440), start_seconds=0, duration_seconds=1),
        ),
        music=tone(tmp_path / "m.wav", 4, 220),
        music_volume=0.5,
        music_ducking=0.5,
        fade_seconds=0,
    )
    media = (
        build_provider_catalog(InMemorySecrets(), tmp_path).resolver([]).resolve(Capability.MEDIA)
    )
    video = media.compose_video(composition, tmp_path / "out.mp4")
    assert mean_volume_after(video, 2.0) > -40.0
