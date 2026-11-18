from __future__ import annotations

import importlib
import json
import re
import sys
import wave
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

Audio = npt.NDArray[np.float32]
ModelLoader = Callable[[str], Any]
SENTENCE_END = re.compile("(?<=[.!?।॥])\\s+")


def sentences(text: str, split: bool) -> list[str]:
    stripped = text.strip()
    if not split:
        return [stripped]
    return [part for part in SENTENCE_END.split(stripped) if part]


def joined(chunks: Sequence[Audio], sample_rate: int, pause_ms: int) -> Audio:
    gap = np.zeros(round(sample_rate * pause_ms / 1000), dtype=np.float32)
    pieces: list[Audio] = []
    for index, chunk in enumerate(chunks):
        if index:
            pieces.append(gap)
        pieces.append(chunk)
    return np.concatenate(pieces)


def write_pcm16(path: str, samples: Audio, sample_rate: int) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def spoken(model: Any, text: str, kwargs: dict[str, Any]) -> tuple[Audio, int]:
    pieces: list[Audio] = []
    sample_rate = 0
    for result in model.generate(text=text, **kwargs):
        pieces.append(np.asarray(result.audio, dtype=np.float32).reshape(-1))
        sample_rate = int(result.sample_rate)
    if not pieces:
        return np.zeros(0, dtype=np.float32), 0
    return np.concatenate(pieces), sample_rate


def render(job: dict[str, Any], load_model: ModelLoader) -> None:
    model = load_model(str(job["model_dir"]))
    texts = sentences(str(job["text"]), bool(job["sentence_split"]))
    rendered = [spoken(model, text, dict(job["kwargs"])) for text in texts]
    sample_rate = max((rate for _, rate in rendered), default=0)
    if sample_rate == 0:
        raise SystemExit("mlx-audio produced no audio")
    audio = joined([chunk for chunk, _ in rendered], sample_rate, int(job["pause_ms"]))
    write_pcm16(str(job["output"]), audio, sample_rate)


def mlx_audio_loader() -> ModelLoader:
    utils: Any = importlib.import_module("mlx_audio.tts.utils")
    loader: ModelLoader = utils.load_model
    return loader


if __name__ == "__main__":
    render(json.load(sys.stdin), mlx_audio_loader())
