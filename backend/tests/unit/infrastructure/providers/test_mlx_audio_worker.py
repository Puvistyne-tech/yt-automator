from __future__ import annotations

import wave
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest

from autotube.infrastructure.providers.tts.mlx_audio_worker import joined, render, sentences

RATE = 24000


@dataclass(frozen=True)
class Result:
    audio: npt.NDArray[np.float32]
    sample_rate: int


class FakeModel:
    def __init__(self, pieces_per_text: int) -> None:
        self.pieces_per_text = pieces_per_text
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def generate(self, text: str, **kwargs: Any) -> Iterator[Result]:
        self.calls.append((text, kwargs))
        for _ in range(self.pieces_per_text):
            yield Result(audio=np.full(RATE // 10, 0.5, dtype=np.float32), sample_rate=RATE)


def read_mono(path: Path) -> tuple[int, int, int, npt.NDArray[np.int16]]:
    with wave.open(str(path)) as handle:
        frames = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
        return handle.getframerate(), handle.getnchannels(), handle.getsampwidth(), frames


def job(output: Path, split: bool, pause_ms: int) -> dict[str, Any]:
    return {
        "model_dir": "/models/m",
        "text": "ஒரு யானை. அது பெரியது! वह बड़ा है। ok",
        "kwargs": {"voice": "Kayal"},
        "sentence_split": split,
        "pause_ms": pause_ms,
        "output": str(output),
    }


def test_sentences_split_on_latin_and_indic_full_stops() -> None:
    text = " One. Two! Three? चार। पाँच॥ six "
    assert sentences(text, True) == ["One.", "Two!", "Three?", "चार।", "पाँच॥", "six"]
    assert sentences(text, False) == ["One. Two! Three? चार। पाँच॥ six"]


def test_joined_puts_silence_between_chunks_only() -> None:
    chunk = np.ones(10, dtype=np.float32)
    audio = joined([chunk, chunk, chunk], 1000, 5)
    assert len(audio) == 40
    assert audio[10:15].tolist() == [0.0] * 5
    assert len(joined([chunk], 1000, 5)) == 10


def test_render_generates_per_sentence_with_pauses(tmp_path: Path) -> None:
    model = FakeModel(pieces_per_text=2)
    loaded: list[str] = []

    def load(path: str) -> FakeModel:
        loaded.append(path)
        return model

    render(job(tmp_path / "o.wav", True, 250), load)
    rate, channels, width, frames = read_mono(tmp_path / "o.wav")
    assert loaded == ["/models/m"]
    assert [text for text, _ in model.calls] == ["ஒரு யானை.", "அது பெரியது!", "वह बड़ा है।", "ok"]
    assert model.calls[0][1] == {"voice": "Kayal"}
    assert (rate, channels, width) == (RATE, 1, 2)
    assert len(frames) == 4 * 2 * RATE // 10 + 3 * RATE // 4
    assert frames[0] == 16383


def test_render_without_split_speaks_once(tmp_path: Path) -> None:
    model = FakeModel(pieces_per_text=1)
    render(job(tmp_path / "o.wav", False, 250), lambda _: model)
    assert len(model.calls) == 1
    assert len(read_mono(tmp_path / "o.wav")[3]) == RATE // 10


def test_render_refuses_a_model_that_yields_nothing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="mlx-audio produced no audio"):
        render(job(tmp_path / "o.wav", True, 0), lambda _: FakeModel(pieces_per_text=0))
    assert not (tmp_path / "o.wav").exists()
