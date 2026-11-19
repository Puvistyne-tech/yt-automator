from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path
from typing import Any, Protocol, cast

from autotube.domain.capabilities import (
    Capability,
    CapabilityProvider,
    ImageGenerator,
    ImageRequest,
    MediaToolkit,
    MotionGenerator,
    MotionRequest,
    MusicGenerator,
    MusicRequest,
    Speech,
    SpeechRequest,
    SpeechSynthesizer,
    TextGenerator,
    TextRequest,
    VideoComposition,
)
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.infrastructure.providers.fallback_log import FallbackRecorder, ignore_fallback
from autotube.infrastructure.providers.upstream_errors import as_upstream
from autotube.shared.errors import UpstreamFailure


class Identified(Protocol):
    @property
    def provider_id(self) -> str: ...


class FallbackChain[P: Identified]:
    def __init__(
        self,
        capability: Capability,
        providers: Sequence[P],
        record: FallbackRecorder = ignore_fallback,
    ) -> None:
        self.capability = capability
        self.providers = list(providers)
        self.record = record
        self.served_by = self.providers[0].provider_id
        self.failures: list[str] = []

    def call[T](self, operation: Callable[[P], T]) -> T:
        failed: list[tuple[str, str]] = []
        for provider in self.providers:
            try:
                result = as_upstream(provider.provider_id, partial(operation, provider))
            except UpstreamFailure as error:
                failed.append((provider.provider_id, error.message))
                continue
            self.served(provider.provider_id, failed)
            return result
        self.failures = described(failed)
        raise UpstreamFailure(
            f"every {self.capability.value} provider failed: {'; '.join(self.failures)}"
        )

    def served(self, provider_id: str, failed: list[tuple[str, str]]) -> None:
        self.served_by = provider_id
        self.failures = described(failed)
        for failed_id, reason in failed:
            fallback = ProviderFallback(
                capability=self.capability, failed=failed_id, used=provider_id, reason=reason
            )
            self.record(fallback)


def described(failed: list[tuple[str, str]]) -> list[str]:
    return [f"{provider_id}: {reason}" for provider_id, reason in failed]


class ChainProxy[P: Identified]:
    def __init__(self, chain: FallbackChain[P]) -> None:
        self.chain = chain

    @property
    def provider_id(self) -> str:
        return self.chain.served_by


class FallbackText(ChainProxy[TextGenerator]):
    def generate(self, request: TextRequest) -> str:
        return self.chain.call(lambda provider: provider.generate(request))


class FallbackImage(ChainProxy[ImageGenerator]):
    def generate(self, request: ImageRequest, output: Path) -> Path:
        return self.chain.call(lambda provider: provider.generate(request, output))


class FallbackMotion(ChainProxy[MotionGenerator]):
    def animate(self, request: MotionRequest, output: Path) -> Path:
        return self.chain.call(lambda provider: provider.animate(request, output))


class FallbackSpeech(ChainProxy[SpeechSynthesizer]):
    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        return self.chain.call(lambda provider: provider.synthesize(request, output))


class FallbackMusic(ChainProxy[MusicGenerator]):
    def compose(self, request: MusicRequest, output: Path) -> Path:
        return self.chain.call(lambda provider: provider.compose(request, output))


class FallbackMedia(ChainProxy[MediaToolkit]):
    def duration_seconds(self, media: Path) -> float:
        return self.chain.call(lambda provider: provider.duration_seconds(media))

    def compose_video(self, composition: VideoComposition, output: Path) -> Path:
        return self.chain.call(lambda provider: provider.compose_video(composition, output))

    def extract_frame(self, video: Path, at_seconds: float, output: Path) -> Path:
        return self.chain.call(lambda provider: provider.extract_frame(video, at_seconds, output))

    def loudness_lufs(self, media: Path) -> float:
        return self.chain.call(lambda provider: provider.loudness_lufs(media))


PROXIES: dict[Capability, type[ChainProxy[Any]]] = {
    Capability.LLM: FallbackText,
    Capability.IMAGE: FallbackImage,
    Capability.MOTION: FallbackMotion,
    Capability.TTS: FallbackSpeech,
    Capability.MUSIC: FallbackMusic,
    Capability.MEDIA: FallbackMedia,
}


def fallback_proxy(
    capability: Capability,
    providers: Sequence[Any],
    record: FallbackRecorder = ignore_fallback,
) -> CapabilityProvider:
    proxy = PROXIES[capability](FallbackChain(capability, providers, record))
    return cast(CapabilityProvider, proxy)
