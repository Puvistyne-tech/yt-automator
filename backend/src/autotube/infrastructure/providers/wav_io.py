from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import numpy.typing as npt

from autotube.infrastructure.providers.output_path import ensure_parent
from autotube.shared.errors import UpstreamFailure

Samples = npt.NDArray[np.float64]


def write_wav(path: Path, samples: Samples, sample_rate: int) -> Path:
    frames = samples if samples.ndim == 2 else samples[:, None]
    pcm = (np.clip(frames, -1.0, 1.0) * 32767).astype("<i2")
    ensure_parent(path)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(frames.shape[1])
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return path


def wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            duration = handle.getnframes() / float(handle.getframerate())
    except (OSError, wave.Error, EOFError) as error:
        raise UpstreamFailure(f"cannot read audio {path.name}: {error}") from error
    if duration <= 0:
        raise UpstreamFailure(f"audio {path.name} is empty")
    return duration
