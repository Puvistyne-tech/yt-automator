from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from autotube.domain.capabilities import WordTiming
from autotube.infrastructure.providers.wav_io import Samples
from autotube.infrastructure.providers.word_normalisation import normalised
from autotube.shared.errors import UpstreamFailure

KOKORO_SAMPLE_RATE = 24000


@dataclass(frozen=True)
class KokoroAudio:
    samples: Samples
    words: tuple[WordTiming, ...]


class KokoroEngine(Protocol):
    def speak(self, text: str, voice: str, speed: float, lang_code: str) -> KokoroAudio: ...


def token_timings(tokens: Any, offset: float) -> list[WordTiming]:
    timings = []
    for token in tokens or []:
        start, end = getattr(token, "start_ts", None), getattr(token, "end_ts", None)
        text = str(getattr(token, "text", ""))
        if start is None or end is None or not normalised(text):
            continue
        timings.append(
            WordTiming(
                word=text, start_seconds=offset + float(start), end_seconds=offset + float(end)
            )
        )
    return timings


class KokoroLibrary:
    def __init__(self) -> None:
        self.pipelines: dict[str, Any] = {}

    def pipeline(self, lang_code: str) -> Any:
        if lang_code not in self.pipelines:
            module: Any = importlib.import_module("kokoro")
            self.pipelines[lang_code] = module.KPipeline(lang_code=lang_code)
        return self.pipelines[lang_code]

    def speak(self, text: str, voice: str, speed: float, lang_code: str) -> KokoroAudio:
        try:
            return self.render(text, voice, speed, lang_code)
        except Exception as error:
            raise UpstreamFailure(f"kokoro failed: {type(error).__name__}: {error}") from error

    def render(self, text: str, voice: str, speed: float, lang_code: str) -> KokoroAudio:
        pieces: list[Samples] = []
        words: list[WordTiming] = []
        offset = 0.0
        for result in self.pipeline(lang_code)(text, voice=voice, speed=speed):
            audio = np.asarray(result.audio, dtype=np.float64).reshape(-1)
            words.extend(token_timings(getattr(result, "tokens", None), offset))
            pieces.append(audio)
            offset += len(audio) / KOKORO_SAMPLE_RATE
        if not pieces:
            raise UpstreamFailure("kokoro produced no audio")
        return KokoroAudio(samples=np.concatenate(pieces), words=tuple(words))
