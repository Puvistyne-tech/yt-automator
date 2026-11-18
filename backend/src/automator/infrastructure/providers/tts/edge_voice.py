from __future__ import annotations

from pathlib import Path

from pydantic import Field

from automator.domain.capabilities import (
    Capability,
    Speech,
    SpeechRequest,
    TimingSource,
    WordTiming,
)
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.host import first_reason
from automator.infrastructure.providers.spec import ProviderOptions, ProviderSpec
from automator.infrastructure.providers.tts.edge_stream import EdgeChunk, EdgeStream, EdgeTtsLibrary
from automator.infrastructure.providers.tts.voice_language import lookup_language
from automator.infrastructure.providers.tts.word_timing import estimate_timings, spoken_words
from automator.infrastructure.providers.wav_io import wav_duration
from automator.shared.errors import UpstreamFailure


class EdgeTtsOptions(ProviderOptions):
    voices: dict[str, str] = Field(
        default_factory=lambda: {"en": "en-IN-NeerjaNeural", "ta": "ta-IN-PallaviNeural"},
        title="Voices by language",
        description="Edge neural voice for each language code, unless the request names a voice.",
    )
    ffmpeg_binary: str = Field(
        default="ffmpeg", title="ffmpeg command", description="Used to convert MP3 to WAV."
    )
    sample_rate: int = Field(
        default=24000, ge=8000, le=96000, title="Sample rate", description="WAV rate in Hz."
    )
    timeout_seconds: float = Field(
        default=120.0, gt=0, title="Timeout", description="Seconds allowed for the conversion."
    )


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
    return [
        binary,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        str(output),
    ]


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
        voice = request.voice or lookup_language(self.options.voices, request.language)
        if not voice:
            raise UpstreamFailure(f"edge_tts has no voice configured for {request.language!r}")
        return voice

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        chunks = self.stream.stream(request.text, self.voice_for(request), edge_rate(request.speed))
        audio = b"".join(chunk.data for chunk in chunks if chunk.kind == "audio")
        if not audio:
            raise UpstreamFailure("edge_tts returned no audio")
        output.parent.mkdir(parents=True, exist_ok=True)
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
