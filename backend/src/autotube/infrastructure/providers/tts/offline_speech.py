from __future__ import annotations

from pathlib import Path

import numpy as np
from pydantic import Field

from autotube.domain.capabilities import (
    Capability,
    Speech,
    SpeechRequest,
    TimingSource,
    WordTiming,
)
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from autotube.infrastructure.providers.tts.speech_text import require_text
from autotube.infrastructure.providers.tts.word_timing import estimate_timings, spoken_words
from autotube.infrastructure.providers.wav_io import Samples, write_wav


class OfflineSpeechOptions(ProviderOptions):
    words_per_minute: int = Field(
        default=150, ge=30, le=600, title="Pace", description="Words per minute at speed 1."
    )
    tone_hz: float = Field(
        default=196.0, gt=20, le=2000, title="Tone", description="Pitch of the soft hum per word."
    )
    volume: float = Field(
        default=0.15, ge=0.0, le=1.0, title="Volume", description="Peak level of the hum."
    )
    sample_rate: int = Field(
        default=24000, ge=8000, le=96000, title="Sample rate", description="Output rate in Hz."
    )
    lead_seconds: float = Field(
        default=0.2, ge=0.0, title="Lead silence", description="Silence before the first word."
    )
    tail_seconds: float = Field(
        default=0.3, ge=0.0, title="Tail silence", description="Silence after the last word."
    )


def speaking_seconds(words: int, request: SpeechRequest, options: OfflineSpeechOptions) -> float:
    return max(words, 1) * 60.0 / (options.words_per_minute * request.speed)


def hum(timings: tuple[WordTiming, ...], total: float, options: OfflineSpeechOptions) -> Samples:
    rate = options.sample_rate
    track = np.zeros(max(1, round(total * rate)), dtype=np.float64)
    for index, timing in enumerate(timings):
        start = round(timing.start_seconds * rate)
        count = max(1, round((timing.end_seconds - timing.start_seconds) * rate))
        clock = np.arange(count) / rate
        pitch = options.tone_hz * (1.0 + 0.06 * ((index % 3) - 1))
        tone = np.sin(2 * np.pi * pitch * clock) + 0.3 * np.sin(4 * np.pi * pitch * clock)
        segment = tone * np.hanning(count) * options.volume / 1.3
        track[start : start + count] += segment[: len(track) - start]
    return track


class OfflineSpeech:
    provider_id = "offline_speech"

    def __init__(self, options: OfflineSpeechOptions, context: ProviderContext) -> None:
        self.options = options
        self.context = context

    def available(self) -> str | None:
        return None

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        words = spoken_words(require_text(self.provider_id, request))
        lead = self.options.lead_seconds
        speaking_end = lead + speaking_seconds(len(words), request, self.options)
        total = speaking_end + self.options.tail_seconds
        timings = estimate_timings(words, lead, speaking_end)
        write_wav(output, hum(timings, total, self.options), self.options.sample_rate)
        return Speech(
            path=output,
            duration_seconds=round(total, 3),
            words=timings,
            timing_source=TimingSource.ESTIMATE,
        )


SPEC = ProviderSpec(
    provider_id=OfflineSpeech.provider_id,
    capability=Capability.TTS,
    name="Offline placeholder voice",
    description="A soft hum per word with estimated timings. Always available, any language.",
    options=OfflineSpeechOptions,
    factory=OfflineSpeech,
    offline=True,
)
