from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, overload

from pydantic import ValidationError

from automator.domain.capabilities import (
    Capability,
    CapabilityProvider,
    ImageGenerator,
    MediaToolkit,
    MotionGenerator,
    MusicGenerator,
    SpeechSynthesizer,
    TextGenerator,
)
from automator.domain.providers import ProviderChoice, ProviderConfig
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.fallback import fallback_proxy
from automator.infrastructure.providers.registry import AnySpec, default_order
from automator.shared.errors import RuleConflict, ValidationFailed


def option_errors(capability: Capability, position: int, error: ValidationError) -> dict[str, str]:
    prefix = f"{capability.value}.chain.{position}.options"
    return {
        ".".join([prefix, *(str(part) for part in item["loc"])]): item["msg"]
        for item in error.errors()
    }


class ChainResolver:
    def __init__(
        self,
        specs: Mapping[str, AnySpec],
        configs: Sequence[ProviderConfig],
        context: ProviderContext,
    ) -> None:
        self.specs = dict(specs)
        self.configs = {config.capability: config for config in configs}
        self.context = context

    def choices(self, capability: Capability) -> tuple[ProviderChoice, ...]:
        config = self.configs.get(capability)
        if config is not None and config.chain:
            return config.chain
        ordered = default_order(capability, tuple(self.specs.values()))
        return tuple(ProviderChoice(provider_id=provider_id) for provider_id in ordered)

    def adapter(
        self, capability: Capability, position: int, choice: ProviderChoice
    ) -> tuple[Any, str | None]:
        spec = self.specs.get(choice.provider_id)
        if spec is None or spec.capability is not capability:
            return None, f"{choice.provider_id}: unknown {capability.value} provider"
        if not choice.enabled:
            return None, f"{choice.provider_id}: disabled"
        try:
            adapter = spec.build(choice.options, self.context)
        except ValidationError as error:
            raise ValidationFailed(option_errors(capability, position, error)) from error
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
        for position, choice in enumerate(self.choices(capability)):
            adapter, reason = self.adapter(capability, position, choice)
            if adapter is None:
                reasons.append(reason or choice.provider_id)
            else:
                ready.append(adapter)
        if not ready:
            detail = "; ".join(reasons) or "no provider is configured"
            message = f"No {capability.value} provider is available: {detail}"
            raise RuleConflict("provider_unavailable", message)
        return fallback_proxy(capability, ready)
