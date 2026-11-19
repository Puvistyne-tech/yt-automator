from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, overload

from pydantic import ValidationError

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
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.providers import ProviderChoice, ProviderConfig
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.fallback import fallback_proxy
from autotube.infrastructure.providers.fallback_log import FallbackLog
from autotube.infrastructure.providers.option_validation import invalid_options_reason
from autotube.infrastructure.providers.registry import AnySpec, default_order
from autotube.shared.errors import RuleConflict


class ChainResolver:
    def __init__(
        self,
        specs: Mapping[str, AnySpec],
        configs: Sequence[ProviderConfig],
        context: ProviderContext,
        secret_names: Sequence[str] = (),
    ) -> None:
        self.specs = dict(specs)
        self.configs = {config.capability: config for config in configs}
        self.context = context
        self.skipped: dict[Capability, list[str]] = {}
        self.fallback_log = FallbackLog(context.secrets, secret_names)

    def fallbacks(self) -> tuple[ProviderFallback, ...]:
        return tuple(self.fallback_log.entries)

    def choices(self, capability: Capability) -> tuple[ProviderChoice, ...]:
        config = self.configs.get(capability)
        if config is not None and config.chain:
            return config.chain
        ordered = default_order(capability, tuple(self.specs.values()))
        return tuple(ProviderChoice(provider_id=provider_id) for provider_id in ordered)

    def adapter(self, capability: Capability, choice: ProviderChoice) -> tuple[Any, str | None]:
        spec = self.specs.get(choice.provider_id)
        if spec is None or spec.capability is not capability:
            return None, f"{choice.provider_id}: unknown {capability.value} provider"
        if not choice.enabled:
            return None, f"{choice.provider_id}: disabled"
        try:
            adapter = spec.build(choice.options, self.context)
        except ValidationError as error:
            return None, f"{choice.provider_id}: {invalid_options_reason(error)}"
        reason = adapter.available()
        return (None, f"{choice.provider_id}: {reason}") if reason else (adapter, None)

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

    def resolve(self, capability: Capability) -> CapabilityProvider:
        ready: list[Any] = []
        reasons: list[str] = []
        for choice in self.choices(capability):
            adapter, reason = self.adapter(capability, choice)
            if adapter is None:
                reasons.append(reason or choice.provider_id)
            else:
                ready.append(adapter)
        self.skipped[capability] = reasons
        if not ready:
            detail = "; ".join(reasons) or "no provider is configured"
            message = f"No {capability.value} provider is available: {detail}"
            raise RuleConflict("provider_unavailable", message)
        return fallback_proxy(capability, ready, self.fallback_log.record)
