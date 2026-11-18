from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from automator.domain.capabilities import (
    Capability,
    ImageRequest,
    MotionRequest,
    MusicRequest,
    Speech,
    SpeechRequest,
    TextRequest,
    TimedClip,
    VideoComposition,
)
from automator.infrastructure.providers.fallback import FallbackChain, fallback_proxy
from automator.infrastructure.providers.tts.espeak import EspeakOptions, EspeakSpeech
from automator.infrastructure.providers.tts.kokoro_voice import KokoroOptions, KokoroSpeech
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import (
    FakeKokoro,
    RecordingRunner,
    make_context,
    writes_wav_after,
)

OUT = Path("/w/out")
STILL = TimedClip(path=Path("/w/a.png"), start_seconds=0, duration_seconds=1)
CALLS: dict[str, Callable[[Any], Any]] = {
    "llm": lambda proxy: proxy.generate(TextRequest(prompt="p")),
    "image": lambda proxy: proxy.generate(ImageRequest(prompt="p", width=2, height=2), OUT),
    "motion": lambda proxy: proxy.animate(
        MotionRequest(image=OUT, duration_seconds=1, width=2, height=2), OUT
    ),
    "tts": lambda proxy: proxy.synthesize(SpeechRequest(text="hi", language="en"), OUT),
    "music": lambda proxy: proxy.compose(MusicRequest(prompt="p", duration_seconds=1), OUT),
    "duration": lambda proxy: proxy.duration_seconds(OUT),
    "compose": lambda proxy: proxy.compose_video(
        VideoComposition(width=2, height=2, visuals=(STILL,)), OUT
    ),
    "frame": lambda proxy: proxy.extract_frame(OUT, 1.0, OUT),
    "loudness": lambda proxy: proxy.loudness_lufs(OUT),
}
CAPABILITIES = {"duration": "media", "compose": "media", "frame": "media", "loudness": "media"}


class Scripted:
    def __init__(self, provider_id: str, error: Exception | None = None) -> None:
        self.provider_id = provider_id
        self.error = error
        self.calls = 0

    def respond(self, *_: object) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return f"from {self.provider_id}"

    generate = animate = synthesize = compose = respond
    duration_seconds = compose_video = extract_frame = loudness_lufs = respond


@pytest.mark.parametrize("call", list(CALLS))
def test_every_proxy_falls_through_to_the_next_provider(call: str) -> None:
    capability = Capability(CAPABILITIES.get(call, call))
    first, second = Scripted("first", UpstreamFailure("msg")), Scripted("second")
    proxy: Any = fallback_proxy(capability, [first, second])
    assert proxy.provider_id == "first"
    assert CALLS[call](proxy) == "from second"
    assert proxy.provider_id == "second"
    assert proxy.chain.failures == ["first: msg"]


def test_programming_errors_propagate_without_trying_the_next_provider() -> None:
    raiser, spare = Scripted("first", ValueError("boom")), Scripted("second")
    proxy: Any = fallback_proxy(Capability.LLM, [raiser, spare])
    with pytest.raises(ValueError, match="boom"):
        proxy.generate(TextRequest(prompt="p"))
    assert spare.calls == 0
    assert proxy.provider_id == "first"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (PermissionError("read-only disk"), "first could not use its files: read-only disk"),
        (FileNotFoundError("gone"), "first could not use its files: gone"),
    ],
)
def test_file_errors_become_upstream_failures(error: Exception, message: str) -> None:
    chain = FallbackChain(Capability.LLM, [Scripted("first", error), Scripted("second")])
    assert chain.call(lambda provider: provider.respond()) == "from second"
    assert chain.failures == [f"first: {message}"]


def test_every_failure_is_reported_when_nothing_serves() -> None:
    chain = FallbackChain(
        Capability.MUSIC, [Scripted("a", UpstreamFailure("x")), Scripted("b", OSError("y"))]
    )
    with pytest.raises(UpstreamFailure) as raised:
        chain.call(lambda provider: provider.respond())
    assert raised.value.message == (
        "every music provider failed: a: x; b: b could not use its files: y"
    )


def test_silent_kokoro_falls_back_to_espeak(tmp_path: Path) -> None:
    context = make_context(tmp_path, runner=RecordingRunner(effect=writes_wav_after("-w", 1.0)))
    kokoro = KokoroSpeech(KokoroOptions(), context, engine=FakeKokoro(samples=0))
    espeak = EspeakSpeech(EspeakOptions(), context)
    proxy: Any = fallback_proxy(Capability.TTS, [kokoro, espeak])
    speech: Speech = proxy.synthesize(SpeechRequest(text="hi", language="en"), tmp_path / "v.wav")
    assert proxy.provider_id == "espeak"
    assert speech.duration_seconds == pytest.approx(1.0)
    assert proxy.chain.failures == ["kokoro: kokoro produced no audio"]


def test_invalid_provider_output_becomes_an_upstream_failure(tmp_path: Path) -> None:
    def zero_length(_: object) -> Speech:
        return Speech(path=tmp_path / "v.wav", duration_seconds=0.0)

    chain = FallbackChain(Capability.TTS, [Scripted("first")])
    with pytest.raises(UpstreamFailure, match="first returned unusable output: Input should be"):
        chain.call(zero_length)
