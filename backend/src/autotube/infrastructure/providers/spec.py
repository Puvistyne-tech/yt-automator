from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, JsonValue

from autotube.domain.capabilities import Capability
from autotube.domain.providers import ProviderDescriptor
from autotube.infrastructure.providers.context import ProviderContext


class ProviderOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Adapter(Protocol):
    @property
    def provider_id(self) -> str: ...

    def available(self) -> str | None: ...


@dataclass(frozen=True)
class ProviderSpec[O: ProviderOptions, A: Adapter]:
    provider_id: str
    capability: Capability
    name: str
    description: str
    options: type[O]
    factory: Callable[[O, ProviderContext], A]
    offline: bool
    required_secrets: tuple[str, ...] = ()

    def build(self, raw: Mapping[str, JsonValue], context: ProviderContext) -> A:
        return self.factory(self.options.model_validate(dict(raw)), context)

    def default(self, context: ProviderContext) -> A:
        return self.factory(self.options(), context)

    def descriptor(self, reason: str | None) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            capability=self.capability,
            name=self.name,
            description=self.description,
            options_schema=self.options.model_json_schema(),
            required_secrets=self.required_secrets,
            offline=self.offline,
            available=reason is None,
            unavailable_reason=reason or "",
        )
