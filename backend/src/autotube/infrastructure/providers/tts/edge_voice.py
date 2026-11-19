from __future__ import annotations

import re
from pathlib import Path

from pydantic import Field, field_validator

from autotube.domain.capabilities import (
    Capability,
    Speech,
    SpeechRequest,
    TimingSource,
    WordTiming,
)
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.ffmpeg_args import FfmpegBinaryOptions, ffmpeg_command
from autotube.infrastructure.providers.host import first_reason
from autotube.infrastructure.providers.output_path import ensure_parent
from autotube.infrastructure.providers.spec import ProviderSpec
from autotube.infrastructure.providers.tts.edge_stream import EdgeChunk, EdgeStream, EdgeTtsLibrary
from autotube.infrastructure.providers.tts.speech_text import require_text
from autotube.infrastructure.providers.tts.voice_language import lookup_language
from autotube.infrastructure.providers.tts.word_timing import estimate_timings, spoken_words
from autotube.infrastructure.providers.wav_io import wav_duration
from autotube.shared.errors import UpstreamFailure


class EdgeTtsOptions(FfmpegBinaryOptions):
    voices: dict[str, str] = Field(
        default_factory=lambda: {"en": "en-IN-NeerjaNeural", "ta": "ta-IN-PallaviNeural"},
        title="Voices by language",
        description="Edge neural voice for each language code, unless the request names a voice.",
    )
    voice_pattern: str = Field(
        default=r"^[a-z]{2,}-[A-Z]{2,}-.+Neural$",
        title="Voice name pattern",
        description="Regular expression every Edge voice name matches; other voices are refused.",
    )
    sample_rate: int = Field(
        default=24000, ge=8000, le=96000, title="Sample rate", description="WAV rate in Hz."
    )
    timeout_seconds: float = Field(
        default=120.0, gt=0, title="Timeout", description="Seconds allowed for the conversion."
    )

    @field_validator("voice_pattern")
    @classmethod
    def compiles(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"not a regular expression: {error}") from error
        return value


def edge_rate(speed: float) -> str:
    return f"{round((speed - 1.0) * 100):+d}%"


def boundary_timings(chunks: list[EdgeChunk]) -> tuple[WordTiming, ...]:
    return tuple(
        WordTiming(
            word=chunk.text,
            start_seconds=round(chunk.offset_seconds, 3),
            end_seconds=round(chunk.offset_seconds + chunk.duration_seconds, 3),
        )
        for chunk in chunks
        if chunk.kind == "WordBoundary" and chunk.text
    )


def wav_command(binary: str, source: Path, output: Path, sample_rate: int) -> list[str]:
    return ffmpeg_command(
        binary, "-i", str(source), "-ar", str(sample_rate), "-ac", "1", str(output)
    )


class EdgeTtsSpeech:
    provider_id = "edge_tts"

    def __init__(
        self, options: EdgeTtsOptions, context: ProviderContext, stream: EdgeStream | None = None
    ) -> None:
        self.options = options
        self.context = context
        self.stream = stream or EdgeTtsLibrary()

    def available(self) -> str | None:
        host = self.context.host
        return first_reason(
            host.missing_module("edge_tts", "tts"), host.missing_binary(self.options.ffmpeg_binary)
        )

    def voice_for(self, request: SpeechRequest) -> str:
        if request.voice and not re.fullmatch(self.options.voice_pattern, request.voice):
            raise UpstreamFailure(f"edge_tts has no voice {request.voice!r}", "voice_unknown")
        voice = request.voice or lookup_language(self.options.voices, request.language)
        if not voice:
            raise UpstreamFailure(f"edge_tts has no voice configured for {request.language!r}")
        return voice

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        require_text(self.provider_id, request)
        chunks = self.stream.stream(request.text, self.voice_for(request), edge_rate(request.speed))
        audio = b"".join(chunk.data for chunk in chunks if chunk.kind == "audio")
        if not audio:
            raise UpstreamFailure("edge_tts returned no audio")
        ensure_parent(output)
        compressed = output.with_suffix(".edge.mp3")
        compressed.write_bytes(audio)
        command = wav_command(
            self.options.ffmpeg_binary, compressed, output, self.options.sample_rate
        )
        try:
            self.context.runner.run(command, self.options.timeout_seconds)
        finally:
            compressed.unlink(missing_ok=True)
        duration = wav_duration(output)
        words = boundary_timings(chunks)
        if words:
            return Speech(
                path=output,
                duration_seconds=duration,
                words=words,
                timing_source=TimingSource.SYNTHESIZER,
            )
        estimated = estimate_timings(spoken_words(request.text), 0.0, duration)
        return Speech(path=output, duration_seconds=duration, words=estimated)


SPEC = ProviderSpec(
    provider_id=EdgeTtsSpeech.provider_id,
    capability=Capability.TTS,
    name="Microsoft Edge voices",
    description="Free natural neural voices over the network with exact word timings.",
    options=EdgeTtsOptions,
    factory=EdgeTtsSpeech,
    offline=False,
)
