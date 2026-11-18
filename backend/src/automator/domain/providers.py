from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from automator.domain.capabilities import Capability
from automator.domain.model_base import DomainModel, JsonObject
from automator.domain.validation import field_path


class ProviderChoice(DomainModel):
    provider_id: str = Field(min_length=1)
    enabled: bool = True
    options: JsonObject = Field(default_factory=dict)


class ProviderConfig(DomainModel):
    capability: Capability
    chain: tuple[ProviderChoice, ...] = ()


class ProviderDescriptor(DomainModel):
    provider_id: str
    capability: Capability
    name: str
    description: str = ""
    options_schema: JsonObject = Field(default_factory=dict)
    required_secrets: tuple[str, ...] = ()
    offline: bool = True
    available: bool = True
    unavailable_reason: str = ""


class ProvidersView(DomainModel):
    descriptors: tuple[ProviderDescriptor, ...]
    config: tuple[ProviderConfig, ...]


def choice_errors(
    index: int, config: ProviderConfig, known: dict[str, ProviderDescriptor]
) -> dict[str, str]:
    errors: dict[str, str] = {}
    seen: set[str] = set()
    for position, choice in enumerate(config.chain):
        path = field_path(index, "chain", position, "provider_id")
        descriptor = known.get(choice.provider_id)
        if descriptor is None:
            errors[path] = f"unknown provider {choice.provider_id!r}"
        elif descriptor.capability is not config.capability:
            errors[path] = f"provider does not offer {config.capability.value}"
        elif choice.provider_id in seen:
            errors[path] = "provider is listed twice"
        seen.add(choice.provider_id)
    return errors


def provider_config_errors(
    configs: Sequence[ProviderConfig], descriptors: Sequence[ProviderDescriptor]
) -> dict[str, str]:
    known = {descriptor.provider_id: descriptor for descriptor in descriptors}
    errors: dict[str, str] = {}
    seen: set[Capability] = set()
    for index, config in enumerate(configs):
        if config.capability in seen:
            errors[field_path(index, "capability")] = "capability is configured twice"
        seen.add(config.capability)
        errors |= choice_errors(index, config, known)
    return errors
