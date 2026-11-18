from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import Field

from automator.domain.image_style import ImageStyleHints
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
    images: tuple[Path, ...] = ()


class ImageRequest(DomainModel):
    prompt: str
    negative_prompt: str = ""
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    seed: int | None = None
    reference_images: tuple[Path, ...] = ()
    style: ImageStyleHints | None = None


class CameraMove(StrEnum):
    PUSH_IN = "push_in"
    PULL_OUT = "pull_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    RISE = "rise"
    STILL = "still"


class MotionRequest(DomainModel):
    image: Path
    prompt: str = ""
    duration_seconds: float = Field(gt=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    fps: int = Field(default=30, ge=1)
    camera: CameraMove = CameraMove.PUSH_IN
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    held_frame_rate: int | None = Field(default=None, ge=1)


class SpeechRequest(DomainModel):
    text: str
    language: str
    voice: str = ""
    speed: float = Field(default=1.0, gt=0)


class TimingSource(StrEnum):
    SYNTHESIZER = "synthesizer"
    ALIGNMENT = "alignment"
    ESTIMATE = "estimate"


class WordTiming(DomainModel):
    word: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)


class Speech(DomainModel):
    path: Path
    duration_seconds: float = Field(gt=0)
    words: tuple[WordTiming, ...] = ()
    timing_source: TimingSource = TimingSource.ESTIMATE


class MusicRequest(DomainModel):
    prompt: str
    duration_seconds: float = Field(gt=0)


class TimedClip(DomainModel):
    path: Path
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)


class SubtitleStyle(DomainModel):
    burn_in: bool = False
    font_family: str = "Noto Sans"
    font_size: int = Field(default=54, ge=8)
    primary_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    highlight_color: str = "#FFD54A"
    margin_bottom: int = Field(default=90, ge=0)
    margin_sides: int = Field(default=40, ge=0)
    font_file: Path | None = None
    wrap_lines: bool = False


class VideoComposition(DomainModel):
    width: int = Field(
        ge=1, description="Output width in pixels; an odd value is rounded down to even, min 2."
    )
    height: int = Field(
        ge=1, description="Output height in pixels; an odd value is rounded down to even, min 2."
    )
    fps: int = Field(default=30, ge=1)
    visuals: tuple[TimedClip, ...]
    narration: tuple[TimedClip, ...] = ()
    music: Path | None = None
    music_volume: float = Field(default=0.2, ge=0.0, le=1.0)
    music_ducking: float = Field(default=0.5, ge=0.0, le=1.0)
    sound_effects: tuple[TimedClip, ...] = ()
    subtitles: Path | None = None
    subtitle_style: SubtitleStyle = Field(default_factory=SubtitleStyle)
    loudness_lufs: float = Field(default=-16.0, le=0.0)
    fade_seconds: float = Field(default=0.5, ge=0.0)


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

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech: ...


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

    def loudness_lufs(self, media: Path) -> float: ...


CapabilityProvider = (
    TextGenerator
    | ImageGenerator
    | MotionGenerator
    | SpeechSynthesizer
    | MusicGenerator
    | MediaToolkit
)
