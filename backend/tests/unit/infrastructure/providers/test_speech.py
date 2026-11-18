from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from automator.domain.capabilities import SpeechRequest, TimingSource, WordTiming
from automator.infrastructure.providers.tts.edge_stream import EdgeChunk, as_chunk
from automator.infrastructure.providers.tts.edge_voice import EdgeTtsOptions, EdgeTtsSpeech
from automator.infrastructure.providers.tts.espeak import EspeakOptions, EspeakSpeech
from automator.infrastructure.providers.tts.kokoro_voice import KokoroOptions, KokoroSpeech
from automator.infrastructure.providers.tts.offline_speech import (
    OfflineSpeech,
    OfflineSpeechOptions,
)
from automator.infrastructure.providers.tts.whisper_aligner import AlignmentOptions
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import (
    FakeKokoro,
    FakeStream,
    RecordingRunner,
    make_context,
    writes_last_argument_as_wav,
    writes_wav_after,
)


class FixedAligner:
    def __init__(self, words: list[WordTiming] | None) -> None:
        self.words = words
        self.calls: list[tuple[Path, str]] = []

    def recognise(self, audio: Path, language: str) -> list[WordTiming] | None:
        self.calls.append((audio, language))
        return self.words


def heard(word: str, start: float, end: float) -> WordTiming:
    return WordTiming(word=word, start_seconds=start, end_seconds=end)


def test_espeak_command_voice_and_estimated_timings(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=writes_wav_after("-w", 1.2))
    context = make_context(tmp_path, runner=runner)
    adapter = EspeakSpeech(EspeakOptions(), context, aligner=FixedAligner(None))
    request = SpeechRequest(text="ஒரு காட்டில் யானை", language="ta-IN", speed=1.2)
    output = tmp_path / "out.wav"
    speech = adapter.synthesize(request, output)
    assert runner.commands[0][:-1] == [
        "espeak-ng",
        "-v",
        "ta",
        "-s",
        "180",
        "-p",
        "50",
        "-w",
        str(output),
    ]
    assert runner.calls[0].stdin == "ஒரு காட்டில் யானை"
    assert speech.duration_seconds == pytest.approx(1.2)
    assert speech.timing_source is TimingSource.ESTIMATE
    assert [word.word for word in speech.words] == ["ஒரு", "காட்டில்", "யானை"]
    assert speech.words[-1].end_seconds <= 1.2


def test_espeak_upgrades_timings_with_alignment(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=writes_wav_after("-w", 2.0))
    aligner = FixedAligner([heard("Hello,", 0.1, 0.5), heard("world", 0.6, 1.1)])
    adapter = EspeakSpeech(EspeakOptions(), make_context(tmp_path, runner=runner), aligner=aligner)
    request = SpeechRequest(text="Hello there world", language="en", voice="en-us")
    speech = adapter.synthesize(request, tmp_path / "a.wav")
    assert runner.commands[0][2] == "en-us"
    assert speech.timing_source is TimingSource.ALIGNMENT
    assert [word.word for word in speech.words] == ["Hello", "there", "world"]
    assert speech.words[1].start_seconds >= 0.5
    assert speech.words[1].end_seconds <= 0.6


def test_espeak_skips_alignment_when_disabled(tmp_path: Path) -> None:
    runner = RecordingRunner(effect=writes_wav_after("-w", 1.0))
    aligner = FixedAligner([heard("hi", 0, 1)])
    options = EspeakOptions(alignment=AlignmentOptions(enabled=False))
    EspeakSpeech(options, make_context(tmp_path, runner=runner), aligner=aligner).synthesize(
        SpeechRequest(text="hi", language="en"), tmp_path / "a.wav"
    )
    assert aligner.calls == []


def test_offline_speech_follows_words_per_minute(tmp_path: Path) -> None:
    adapter = OfflineSpeech(OfflineSpeechOptions(words_per_minute=120), make_context(tmp_path))
    speech = adapter.synthesize(
        SpeechRequest(text="one two three four", language="xx"), tmp_path / "s.wav"
    )
    assert speech.duration_seconds == pytest.approx(0.2 + 2.0 + 0.3)
    assert speech.words[0].start_seconds == pytest.approx(0.2)
    assert speech.words[-1].end_seconds <= 2.2
    with wave.open(str(speech.path)) as handle:
        assert handle.getframerate() == 24000
        assert handle.getnframes() == 60000
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    assert np.abs(samples[: 24000 // 10]).max() == 0
    assert np.abs(samples).max() > 1000


def test_edge_uses_word_boundaries_and_converts_to_wav(tmp_path: Path) -> None:
    chunks = [
        EdgeChunk(kind="audio", data=b"mp3"),
        as_chunk(
            {"type": "WordBoundary", "offset": 1_000_000, "duration": 4_000_000, "text": "Hi"}
        ),
        as_chunk(
            {"type": "WordBoundary", "offset": 6_000_000, "duration": 3_000_000, "text": "you"}
        ),
    ]
    stream = FakeStream(chunks)
    runner = RecordingRunner(effect=writes_last_argument_as_wav(1.0))
    adapter = EdgeTtsSpeech(EdgeTtsOptions(), make_context(tmp_path, runner=runner), stream=stream)
    speech = adapter.synthesize(
        SpeechRequest(text="Hi you", language="en-IN", speed=0.9), tmp_path / "e.wav"
    )
    assert stream.calls == [("Hi you", "en-IN-NeerjaNeural", "-10%")]
    assert runner.commands[0][6] == str(tmp_path / "e.edge.mp3")
    assert not (tmp_path / "e.edge.mp3").exists()
    assert speech.timing_source is TimingSource.SYNTHESIZER
    assert speech.words == (heard("Hi", 0.1, 0.5), heard("you", 0.6, 0.9))


def test_kokoro_maps_language_and_keeps_engine_timings(tmp_path: Path) -> None:
    engine = FakeKokoro((heard("Hello", 0.0, 0.4),))
    adapter = KokoroSpeech(KokoroOptions(), make_context(tmp_path), engine=engine)
    speech = adapter.synthesize(SpeechRequest(text="Hello", language="en-GB"), tmp_path / "k.wav")
    assert engine.calls == [("Hello", "af_heart", 1.0, "b")]
    assert speech.duration_seconds == 0.5
    assert speech.timing_source is TimingSource.SYNTHESIZER
    with pytest.raises(UpstreamFailure, match="does not speak"):
        adapter.synthesize(SpeechRequest(text="x", language="ta"), tmp_path / "t.wav")


def test_kokoro_estimates_then_aligns_without_engine_timings(tmp_path: Path) -> None:
    aligner = FixedAligner([heard("Hello", 0.05, 0.3)])
    adapter = KokoroSpeech(
        KokoroOptions(), make_context(tmp_path), engine=FakeKokoro(()), aligner=aligner
    )
    speech = adapter.synthesize(SpeechRequest(text="Hello", language="en"), tmp_path / "k.wav")
    assert speech.timing_source is TimingSource.ALIGNMENT
    assert speech.words == (heard("Hello", 0.05, 0.3),)
