from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from autotube.domain.capabilities import Capability, SpeechRequest, SpeechSynthesizer
from autotube.infrastructure.providers.fallback import fallback_proxy
from autotube.infrastructure.providers.tts.edge_stream import EdgeChunk
from autotube.infrastructure.providers.tts.edge_voice import EdgeTtsOptions, EdgeTtsSpeech
from autotube.infrastructure.providers.tts.kokoro_voice import KokoroOptions, KokoroSpeech
from autotube.infrastructure.providers.tts.mlx_audio_voice import MlxAudioOptions, MlxAudioSpeech
from autotube.infrastructure.providers.tts.whisper_aligner import AlignmentOptions
from autotube.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import (
    FakeKokoro,
    FakeStream,
    RecordingRunner,
    make_context,
    write_tone,
)

QUIET = AlignmentOptions(enabled=False)


@dataclass
class Chain:
    proxy: SpeechSynthesizer
    mlx_runner: RecordingRunner
    edge_stream: FakeStream
    kokoro: FakeKokoro


def mlx_runner() -> RecordingRunner:
    runner = RecordingRunner()

    def effect(_command: list[str]) -> None:
        write_tone(Path(json.loads(runner.calls[-1].stdin or "")["output"]), 1.0, 24000)

    runner.effect = effect
    return runner


def default_order_chain(tmp_path: Path) -> Chain:
    runner, stream, kokoro = (
        mlx_runner(),
        FakeStream([EdgeChunk(kind="audio", data=b"x")]),
        FakeKokoro(),
    )
    mlx = MlxAudioSpeech(MlxAudioOptions(alignment=QUIET), make_context(tmp_path, runner=runner))
    edge = EdgeTtsSpeech(EdgeTtsOptions(), make_context(tmp_path), stream=stream)
    local = KokoroSpeech(KokoroOptions(alignment=QUIET), make_context(tmp_path), engine=kokoro)
    proxy = cast(SpeechSynthesizer, fallback_proxy(Capability.TTS, [mlx, edge, local]))
    return Chain(proxy, runner, stream, kokoro)


def speak(chain: Chain, tmp_path: Path, language: str, voice: str) -> str:
    request = SpeechRequest(text="Once upon a time", language=language, voice=voice)
    chain.proxy.synthesize(request, tmp_path / f"{language}-{voice}.wav")
    return chain.proxy.provider_id


def test_a_kokoro_voice_falls_through_mlx_audio_and_edge_to_kokoro(tmp_path: Path) -> None:
    chain = default_order_chain(tmp_path)
    assert speak(chain, tmp_path, "en", "am_michael") == "kokoro"
    assert [call[1] for call in chain.kokoro.calls] == ["am_michael"]
    assert chain.mlx_runner.calls == []
    assert chain.edge_stream.calls == []


@pytest.mark.parametrize(("language", "voice"), [("en", "news_reader"), ("ta", "vaidehi")])
def test_an_mlx_audio_preset_is_spoken_by_mlx_audio(
    tmp_path: Path, language: str, voice: str
) -> None:
    chain = default_order_chain(tmp_path)
    assert speak(chain, tmp_path, language, voice) == "mlx_audio"
    assert len(chain.mlx_runner.calls) == 1
    assert chain.kokoro.calls == []


def test_kokoro_refuses_a_voice_it_does_not_know(tmp_path: Path) -> None:
    engine = FakeKokoro()
    adapter = KokoroSpeech(KokoroOptions(), make_context(tmp_path), engine=engine)
    request = SpeechRequest(text="hi", language="en", voice="warm_storyteller")
    with pytest.raises(UpstreamFailure, match="^kokoro has no voice 'warm_storyteller'$") as raised:
        adapter.synthesize(request, tmp_path / "k.wav")
    assert raised.value.code == "voice_unknown"
    assert engine.calls == []


def test_kokoro_speaks_a_voice_added_to_its_options(tmp_path: Path) -> None:
    engine = FakeKokoro()
    options = KokoroOptions(voices=["zf_custom"], alignment=QUIET)
    adapter = KokoroSpeech(options, make_context(tmp_path), engine=engine)
    adapter.synthesize(
        SpeechRequest(text="hi", language="en", voice="zf_custom"), tmp_path / "k.wav"
    )
    assert [call[1] for call in engine.calls] == ["zf_custom"]


def test_edge_refuses_a_voice_that_is_not_an_edge_voice_name(tmp_path: Path) -> None:
    stream = FakeStream([])
    adapter = EdgeTtsSpeech(EdgeTtsOptions(), make_context(tmp_path), stream=stream)
    request = SpeechRequest(text="hi", language="en", voice="af_heart")
    with pytest.raises(UpstreamFailure, match="^edge_tts has no voice 'af_heart'$") as raised:
        adapter.synthesize(request, tmp_path / "e.wav")
    assert raised.value.code == "voice_unknown"
    assert stream.calls == []


def test_edge_speaks_a_named_edge_voice(tmp_path: Path) -> None:
    stream = FakeStream([])
    adapter = EdgeTtsSpeech(EdgeTtsOptions(), make_context(tmp_path), stream=stream)
    request = SpeechRequest(text="hi", language="en", voice="en-US-AvaMultilingualNeural")
    with pytest.raises(UpstreamFailure, match="returned no audio"):
        adapter.synthesize(request, tmp_path / "e.wav")
    assert stream.calls == [("hi", "en-US-AvaMultilingualNeural", "+0%")]


def test_edge_options_refuse_a_voice_pattern_that_is_not_a_regular_expression() -> None:
    with pytest.raises(ValidationError, match="not a regular expression"):
        EdgeTtsOptions(voice_pattern="(")
