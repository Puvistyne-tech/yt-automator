from __future__ import annotations

import importlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field

from autotube.domain.capabilities import Speech, SpeechRequest, TimingSource, WordTiming
from autotube.infrastructure.providers.host import HostProbe
from autotube.infrastructure.providers.spec import ProviderOptions
from autotube.infrastructure.providers.tts.word_alignment import align_words
from autotube.infrastructure.providers.tts.word_timing import spoken_words


class AlignmentOptions(ProviderOptions):
    enabled: bool = Field(
        default=True,
        title="Align with Whisper",
        description="Refine estimated word timings with mlx-whisper or faster-whisper.",
    )
    mlx_model: str = Field(
        default="mlx-community/whisper-large-v3-turbo",
        title="mlx-whisper model",
        description="Hugging Face repo used by mlx-whisper on Apple silicon.",
    )
    faster_whisper_model: str = Field(
        default="small", title="faster-whisper model", description="Model size or path."
    )
    faster_whisper_compute_type: str = Field(
        default="int8",
        min_length=1,
        title="faster-whisper compute type",
        description="CTranslate2 compute type, for example int8, int8_float16 or float32.",
    )
    min_match: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        title="Minimum match",
        description="Share of words the transcript must match before its timings are used.",
    )


class WordAligner(Protocol):
    def recognise(self, audio: Path, language: str) -> list[WordTiming] | None: ...


def timing(word: Any, start: Any, end: Any) -> WordTiming:
    begin = max(0.0, float(start))
    return WordTiming(
        word=str(word).strip(), start_seconds=begin, end_seconds=max(begin, float(end))
    )


def mlx_words(audio: Path, language: str, model: str) -> list[WordTiming]:
    module: Any = importlib.import_module("mlx_whisper")
    result = module.transcribe(
        str(audio), path_or_hf_repo=model, word_timestamps=True, language=language
    )
    segments: Iterable[Any] = result.get("segments", [])
    return [
        timing(word["word"], word["start"], word["end"])
        for segment in segments
        for word in segment.get("words", [])
    ]


def faster_words(audio: Path, language: str, options: AlignmentOptions) -> list[WordTiming]:
    module: Any = importlib.import_module("faster_whisper")
    model = module.WhisperModel(
        options.faster_whisper_model, compute_type=options.faster_whisper_compute_type
    )
    segments, _ = model.transcribe(str(audio), word_timestamps=True, language=language)
    return [
        timing(word.word, word.start, word.end) for segment in segments for word in segment.words
    ]


class WhisperAligner:
    def __init__(self, host: HostProbe, options: AlignmentOptions) -> None:
        self.host = host
        self.options = options

    def recognise(self, audio: Path, language: str) -> list[WordTiming] | None:
        code = language.split("-")[0].lower()
        try:
            if self.host.has_module("mlx_whisper"):
                return mlx_words(audio, code, self.options.mlx_model)
            if self.host.has_module("faster_whisper"):
                return faster_words(audio, code, self.options)
        except Exception:
            return None
        return None


def refine(
    speech: Speech, request: SpeechRequest, aligner: WordAligner, options: AlignmentOptions
) -> Speech:
    if not options.enabled:
        return speech
    recognised = aligner.recognise(speech.path, request.language)
    if not recognised:
        return speech
    words = spoken_words(request.text)
    aligned = align_words(words, recognised, speech.duration_seconds, options.min_match)
    if aligned is None:
        return speech
    return speech.model_copy(update={"words": aligned, "timing_source": TimingSource.ALIGNMENT})
