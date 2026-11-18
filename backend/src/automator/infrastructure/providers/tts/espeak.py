from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import Capability, Speech, SpeechRequest, TimingSource
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from automator.infrastructure.providers.tts.voice_language import (
    language_candidates,
    lookup_language,
)
from automator.infrastructure.providers.tts.whisper_aligner import (
    AlignmentOptions,
    WhisperAligner,
    WordAligner,
    refine,
)
from automator.infrastructure.providers.tts.word_timing import estimate_timings, spoken_words
from automator.infrastructure.providers.wav_io import wav_duration
from automator.shared.errors import UpstreamFailure


class EspeakOptions(ProviderOptions):
    binary: str = Field(default="espeak-ng", title="Command", description="espeak-ng executable.")
    voices: dict[str, str] = Field(
        default_factory=lambda: {"en": "en-gb", "ta": "ta"},
        title="Voices by language",
        description="espeak-ng voice for each language code; other languages use the code itself.",
    )
    words_per_minute: int = Field(
        default=150, ge=60, le=450, title="Speed", description="Words per minute at speed 1."
    )
    pitch: int = Field(default=50, ge=0, le=99, title="Pitch", description="espeak-ng pitch.")
    alignment: AlignmentOptions = Field(
        default_factory=AlignmentOptions,
        title="Alignment",
        description="Optional Whisper alignment of the estimated word timings.",
    )
    timeout_seconds: float = Field(
        default=120.0, gt=0, title="Timeout", description="Seconds allowed per narration."
    )


def espeak_voice(request: SpeechRequest, options: EspeakOptions) -> str:
    chosen = request.voice or lookup_language(options.voices, request.language)
    return chosen or language_candidates(request.language)[-1]


def espeak_command(request: SpeechRequest, options: EspeakOptions, output: Path) -> list[str]:
    rate = round(options.words_per_minute * request.speed)
    return [
        options.binary,
        "-v",
        espeak_voice(request, options),
        "-s",
        str(rate),
        "-p",
        str(options.pitch),
        "-w",
        str(output),
        "--stdin",
    ]


class EspeakSpeech:
    provider_id = "espeak"

    def __init__(
        self, options: EspeakOptions, context: ProviderContext, aligner: WordAligner | None = None
    ) -> None:
        self.options = options
        self.context = context
        self.aligner = aligner or WhisperAligner(context.host, options.alignment)

    def available(self) -> str | None:
        return self.context.host.missing_binary(self.options.binary)

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        if not request.text.strip():
            raise UpstreamFailure("espeak needs some text to speak")
        output.parent.mkdir(parents=True, exist_ok=True)
        command = espeak_command(request, self.options, output)
        self.context.runner.run(command, self.options.timeout_seconds, stdin=request.text)
        duration = wav_duration(output)
        speech = Speech(
            path=output,
            duration_seconds=duration,
            words=estimate_timings(spoken_words(request.text), 0.0, duration),
            timing_source=TimingSource.ESTIMATE,
        )
        return refine(speech, request, self.aligner, self.options.alignment)


SPEC = ProviderSpec(
    provider_id=EspeakSpeech.provider_id,
    capability=Capability.TTS,
    name="eSpeak NG",
    description="Robotic but fully offline voices in many languages, including Tamil.",
    options=EspeakOptions,
    factory=EspeakSpeech,
    offline=True,
)
