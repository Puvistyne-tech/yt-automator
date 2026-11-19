from __future__ import annotations

from pathlib import Path

from pydantic import Field

from autotube.domain.capabilities import Capability, Speech, SpeechRequest, TimingSource
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from autotube.infrastructure.providers.tts.kokoro_engine import (
    KOKORO_SAMPLE_RATE,
    KokoroEngine,
    KokoroLibrary,
)
from autotube.infrastructure.providers.tts.speech_text import require_text
from autotube.infrastructure.providers.tts.voice_language import lookup_language
from autotube.infrastructure.providers.tts.whisper_aligner import (
    AlignmentOptions,
    WhisperAligner,
    WordAligner,
    estimated_speech,
)
from autotube.infrastructure.providers.wav_io import write_wav
from autotube.shared.errors import UpstreamFailure

KOKORO_LANGUAGES = {"en": "a", "en-us": "a", "en-gb": "b", "hi": "h", "es": "e", "fr": "f"}


class KokoroOptions(ProviderOptions):
    voice: str = Field(
        default="af_heart",
        title="Voice",
        description="Kokoro voice id used when the request names none.",
    )
    languages: dict[str, str] = Field(
        default_factory=lambda: dict(KOKORO_LANGUAGES),
        title="Language codes",
        description="Kokoro pipeline code for each supported language; others fall back.",
    )
    alignment: AlignmentOptions = Field(
        default_factory=AlignmentOptions,
        title="Alignment",
        description="Whisper alignment used when Kokoro gives no word timestamps.",
    )


class KokoroSpeech:
    provider_id = "kokoro"

    def __init__(
        self,
        options: KokoroOptions,
        context: ProviderContext,
        engine: KokoroEngine | None = None,
        aligner: WordAligner | None = None,
    ) -> None:
        self.options = options
        self.context = context
        self.engine = engine or KokoroLibrary()
        self.aligner = aligner or WhisperAligner(context.host, options.alignment)

    def available(self) -> str | None:
        return self.context.host.missing_module("kokoro", "tts")

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        require_text(self.provider_id, request)
        lang_code = lookup_language(self.options.languages, request.language)
        if lang_code is None:
            raise UpstreamFailure(
                f"kokoro does not speak {request.language!r}", "language_unsupported"
            )
        voice = request.voice or self.options.voice
        audio = self.engine.speak(request.text, voice, request.speed, lang_code)
        if len(audio.samples) == 0:
            raise UpstreamFailure("kokoro produced no audio")
        write_wav(output, audio.samples, KOKORO_SAMPLE_RATE)
        duration = round(len(audio.samples) / KOKORO_SAMPLE_RATE, 3)
        if audio.words:
            return Speech(
                path=output,
                duration_seconds=duration,
                words=audio.words,
                timing_source=TimingSource.SYNTHESIZER,
            )
        return estimated_speech(output, duration, request, self.aligner, self.options.alignment)


SPEC = ProviderSpec(
    provider_id=KokoroSpeech.provider_id,
    capability=Capability.TTS,
    name="Kokoro (local)",
    description="Natural local neural voices for English and a few other languages.",
    options=KokoroOptions,
    factory=KokoroSpeech,
    offline=True,
)
