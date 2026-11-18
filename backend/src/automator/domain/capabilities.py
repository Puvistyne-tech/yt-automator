from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import Field

from automator.domain.model_base import DomainModel, JsonObject


class Capability(StrEnum):
    LLM = "llm"
    IMAGE = "image"
    MOTION = "motion"
    TTS = "tts"
    MUSIC = "music"
    MEDIA = "media"


class TextRequest(DomainModel):
    prompt: str
    system: str = ""
    max_tokens: int = Field(default=1024, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    json_schema: JsonObject | None = None


class ImageRequest(DomainModel):
    prompt: str
    negative_prompt: str = ""
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    seed: int | None = None
    reference_images: tuple[Path, ...] = ()


class MotionRequest(DomainModel):
    image: Path
    prompt: str = ""
    duration_seconds: float = Field(gt=0)
    fps: int = Field(default=24, ge=1)


class SpeechRequest(DomainModel):
    text: str
    language: str
    voice: str = ""
    speed: float = Field(default=1.0, gt=0)


class MusicRequest(DomainModel):
    prompt: str
    duration_seconds: float = Field(gt=0)


class TimedClip(DomainModel):
    path: Path
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)


class VideoComposition(DomainModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    fps: int = Field(default=30, ge=1)
    visuals: tuple[TimedClip, ...]
    narration: tuple[TimedClip, ...] = ()
    music: Path | None = None
    music_volume: float = Field(default=0.2, ge=0.0, le=1.0)
    subtitles: Path | None = None


class TextGenerator(Protocol):
    @property
    def provider_id(self) -> str: ...

    def generate(self, request: TextRequest) -> str: ...


class ImageGenerator(Protocol):
    @property
    def provider_id(self) -> str: ...

    def generate(self, request: ImageRequest, output: Path) -> Path: ...


class MotionGenerator(Protocol):
    @property
    def provider_id(self) -> str: ...

    def animate(self, request: MotionRequest, output: Path) -> Path: ...


class SpeechSynthesizer(Protocol):
    @property
    def provider_id(self) -> str: ...

    def synthesize(self, request: SpeechRequest, output: Path) -> Path: ...


class MusicGenerator(Protocol):
    @property
    def provider_id(self) -> str: ...

    def compose(self, request: MusicRequest, output: Path) -> Path: ...


class MediaToolkit(Protocol):
    @property
    def provider_id(self) -> str: ...

    def duration_seconds(self, media: Path) -> float: ...

    def compose_video(self, composition: VideoComposition, output: Path) -> Path: ...

    def extract_frame(self, video: Path, at_seconds: float, output: Path) -> Path: ...


CapabilityProvider = (
    TextGenerator
    | ImageGenerator
    | MotionGenerator
    | SpeechSynthesizer
    | MusicGenerator
    | MediaToolkit
)
