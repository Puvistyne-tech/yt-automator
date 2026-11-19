from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, overload

from pydantic import BaseModel, Field

from autotube.domain.capabilities import (
    Capability,
    CapabilityProvider,
    ImageGenerator,
    MediaToolkit,
    MotionGenerator,
    MusicGenerator,
    SpeechSynthesizer,
    TextGenerator,
)
from autotube.domain.model_base import DomainModel, JsonObject
from autotube.domain.pipeline_descriptors import PipelineDescriptor, StageDescriptor
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.quality import ScoreItem
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.domain.run_parts import Artifact


class ProviderResolver(Protocol):
    @overload
    def resolve(self, capability: Literal[Capability.LLM]) -> TextGenerator: ...
    @overload
    def resolve(self, capability: Literal[Capability.IMAGE]) -> ImageGenerator: ...
    @overload
    def resolve(self, capability: Literal[Capability.MOTION]) -> MotionGenerator: ...
    @overload
    def resolve(self, capability: Literal[Capability.TTS]) -> SpeechSynthesizer: ...
    @overload
    def resolve(self, capability: Literal[Capability.MUSIC]) -> MusicGenerator: ...
    @overload
    def resolve(self, capability: Literal[Capability.MEDIA]) -> MediaToolkit: ...
    @overload
    def resolve(self, capability: Capability) -> CapabilityProvider: ...

    def fallbacks(self) -> tuple[ProviderFallback, ...]: ...


class NewArtifact(DomainModel):
    kind: ArtifactKind
    path: Path
    language: str | None = None
    variant: str | None = None
    media_type: str
    meta: JsonObject = Field(default_factory=dict)


class StageOutcome(DomainModel):
    artifacts: tuple[NewArtifact, ...] = ()
    provider: str = ""
    message: str = ""


class StageLog(Protocol):
    def __call__(self, message: str, level: LogLevel = LogLevel.INFO) -> None: ...


@dataclass(frozen=True)
class StageContext:
    run_id: str
    settings: BaseModel
    languages: tuple[str, ...]
    workspace: Path
    artifacts: tuple[Artifact, ...]
    providers: ProviderResolver
    log: StageLog


class Stage(Protocol):
    @property
    def descriptor(self) -> StageDescriptor: ...

    def run(self, context: StageContext) -> StageOutcome: ...


class Pipeline(Protocol):
    @property
    def descriptor(self) -> PipelineDescriptor: ...

    @property
    def settings_model(self) -> type[BaseModel]: ...

    def stages(self) -> Sequence[Stage]: ...

    def score(self, context: StageContext) -> Sequence[ScoreItem]: ...


def pipeline_not_installed(type_id: str) -> str:
    return f"pipeline {type_id!r} is not installed"
