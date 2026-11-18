from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from automator.domain.capabilities import SpeechRequest, SpeechSynthesizer
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.tts.edge_voice import (
    EdgeTtsOptions,
    EdgeTtsSpeech,
    edge_rate,
)
from automator.infrastructure.providers.tts.espeak import EspeakOptions, EspeakSpeech
from automator.infrastructure.providers.tts.kokoro_voice import KokoroOptions, KokoroSpeech
from automator.infrastructure.providers.tts.offline_speech import (
    OfflineSpeech,
    OfflineSpeechOptions,
)
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import (
    FakeKokoro,
    FakeStream,
    RecordingRunner,
    make_context,
)

SpeechFactory = Callable[[ProviderContext], SpeechSynthesizer]
SYNTHESIZERS: dict[str, SpeechFactory] = {
    "espeak": lambda context: EspeakSpeech(EspeakOptions(), context),
    "offline_speech": lambda context: OfflineSpeech(OfflineSpeechOptions(), context),
    "kokoro": lambda context: KokoroSpeech(KokoroOptions(), context, engine=FakeKokoro()),
}


@pytest.mark.parametrize("provider_id", list(SYNTHESIZERS))
@pytest.mark.parametrize("text", ["", "   "])
def test_blank_text_is_refused(tmp_path: Path, provider_id: str, text: str) -> None:
    runner = RecordingRunner()
    synthesizer = SYNTHESIZERS[provider_id](make_context(tmp_path, runner=runner))
    with pytest.raises(UpstreamFailure, match=f"^{provider_id} needs some text to speak$"):
        synthesizer.synthesize(SpeechRequest(text=text, language="en"), tmp_path / "v.wav")
    assert runner.calls == []
    assert not (tmp_path / "v.wav").exists()


def test_kokoro_refuses_zero_samples(tmp_path: Path) -> None:
    adapter = KokoroSpeech(KokoroOptions(), make_context(tmp_path), engine=FakeKokoro(samples=0))
    with pytest.raises(UpstreamFailure, match="kokoro produced no audio"):
        adapter.synthesize(SpeechRequest(text="hi", language="en"), tmp_path / "v.wav")


def edge(tmp_path: Path) -> EdgeTtsSpeech:
    return EdgeTtsSpeech(EdgeTtsOptions(), make_context(tmp_path), stream=FakeStream([]))


def test_edge_refuses_a_language_without_a_voice(tmp_path: Path) -> None:
    with pytest.raises(UpstreamFailure, match="no voice configured for 'fr'"):
        edge(tmp_path).synthesize(SpeechRequest(text="x", language="fr"), tmp_path / "x.wav")


def test_edge_refuses_a_stream_without_audio(tmp_path: Path) -> None:
    with pytest.raises(UpstreamFailure, match="edge_tts returned no audio"):
        edge(tmp_path).synthesize(SpeechRequest(text="x", language="ta"), tmp_path / "x.wav")


def test_edge_reports_its_missing_package(tmp_path: Path) -> None:
    assert edge(tmp_path).available() == (
        "Python package 'edge_tts' is not installed (uv sync --extra tts)"
    )


@pytest.mark.parametrize(("speed", "rate"), [(1.25, "+25%"), (1.0, "+0%"), (0.9, "-10%")])
def test_edge_rate_is_a_signed_percentage(speed: float, rate: str) -> None:
    assert edge_rate(speed) == rate
