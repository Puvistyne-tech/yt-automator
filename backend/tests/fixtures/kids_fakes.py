from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageFont

from automator.domain.capabilities import (
    Capability,
    ImageRequest,
    MotionRequest,
    MusicRequest,
    Speech,
    SpeechRequest,
    TextRequest,
    TimingSource,
    VideoComposition,
    WordTiming,
)
from automator.domain.run_enums import LogLevel

WORD_SECONDS = {"en": 0.5, "ta": 0.75}
TAIL_SECONDS = 0.2


class LogBook:
    def __init__(self) -> None:
        self.entries: list[tuple[LogLevel, str]] = []

    def __call__(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self.entries.append((level, message))

    @property
    def lines(self) -> list[str]:
        return [message for _, message in self.entries]

    def warnings(self) -> list[str]:
        return [message for level, message in self.entries if level is LogLevel.WARNING]


class FakeWriter:
    provider_id = "fake-llm"

    def __init__(self, respond: Callable[[TextRequest], str]) -> None:
        self.respond = respond
        self.requests: list[TextRequest] = []

    def generate(self, request: TextRequest) -> str:
        self.requests.append(request)
        return self.respond(request)


class FakeImages:
    provider_id = "fake-image"

    def __init__(self) -> None:
        self.requests: list[ImageRequest] = []

    def generate(self, request: ImageRequest, output: Path) -> Path:
        self.requests.append(request)
        shade = (request.seed or 0) % 200
        Image.new("RGB", (request.width, request.height), (shade, 120, 180)).save(output)
        return output


class FakeMotion:
    provider_id = "fake-motion"

    def __init__(self) -> None:
        self.requests: list[MotionRequest] = []

    def animate(self, request: MotionRequest, output: Path) -> Path:
        self.requests.append(request)
        output.write_bytes(b"clip")
        return output


class FakeSpeech:
    provider_id = "fake-tts"

    def __init__(self, with_words: bool = True) -> None:
        self.with_words = with_words
        self.requests: list[SpeechRequest] = []

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        self.requests.append(request)
        output.write_bytes(b"wav")
        words = request.text.split()
        step = WORD_SECONDS.get(request.language, 0.5)
        timings = tuple(
            WordTiming(word=word, start_seconds=index * step, end_seconds=(index + 1) * step - 0.05)
            for index, word in enumerate(words)
        )
        return Speech(
            path=output,
            duration_seconds=len(words) * step + TAIL_SECONDS,
            words=timings if self.with_words else (),
            timing_source=TimingSource.SYNTHESIZER,
        )


class FakeMusic:
    provider_id = "fake-music"

    def __init__(self) -> None:
        self.requests: list[MusicRequest] = []

    def compose(self, request: MusicRequest, output: Path) -> Path:
        self.requests.append(request)
        output.write_bytes(b"music")
        return output


class FakeMedia:
    provider_id = "fake-media"

    def __init__(self, loudness: float = -16.0) -> None:
        self.loudness = loudness
        self.compositions: dict[str, VideoComposition] = {}
        self.measured: list[Path] = []

    def duration_seconds(self, media: Path) -> float:
        composition = self.compositions[media.name]
        return max(clip.start_seconds + clip.duration_seconds for clip in composition.visuals)

    def compose_video(self, composition: VideoComposition, output: Path) -> Path:
        self.compositions[output.name] = composition
        output.write_text(composition.model_dump_json(), encoding="utf-8")
        return output

    def extract_frame(self, video: Path, at_seconds: float, output: Path) -> Path:
        output.write_bytes(f"{video.name}@{at_seconds}".encode())
        return output

    def loudness_lufs(self, media: Path) -> float:
        self.measured.append(media)
        return self.loudness


@dataclass
class FakeProviders:
    writer: FakeWriter | None = None
    images: FakeImages = field(default_factory=FakeImages)
    motion: FakeMotion = field(default_factory=FakeMotion)
    speech: FakeSpeech = field(default_factory=FakeSpeech)
    music: FakeMusic | None = field(default_factory=FakeMusic)
    media: FakeMedia = field(default_factory=FakeMedia)

    def resolve(self, capability: Capability) -> Any:
        found = {
            Capability.LLM: self.writer,
            Capability.IMAGE: self.images,
            Capability.MOTION: self.motion,
            Capability.TTS: self.speech,
            Capability.MUSIC: self.music,
            Capability.MEDIA: self.media,
        }[capability]
        if found is None:
            raise LookupError(f"no provider for {capability.value}")
        return found


def failing_writer() -> FakeWriter:
    def fail(request: TextRequest) -> str:
        raise RuntimeError(f"model offline for {len(request.prompt)} characters")

    return FakeWriter(fail)


def scripted_writer(answers: list[str]) -> FakeWriter:
    remaining = list(answers)

    def respond(request: TextRequest) -> str:
        if not remaining:
            raise RuntimeError(f"no scripted answer left for {request.prompt[:20]}")
        return remaining.pop(0)

    return FakeWriter(respond)


def as_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def embedded_font(folder: Path) -> Path:
    font = ImageFont.load_default(12)
    assert isinstance(font, ImageFont.FreeTypeFont)
    path = folder / "embedded.ttf"
    path.write_bytes(font.font_bytes)
    return path
