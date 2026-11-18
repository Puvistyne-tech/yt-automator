from __future__ import annotations

import builtins
from collections.abc import Sequence
from typing import Protocol

from automator.domain.pipeline import Pipeline, ProviderResolver
from automator.domain.providers import ProviderConfig, ProviderDescriptor
from automator.domain.secrets import SecretDefinition


class PipelineRegistry(Protocol):
    def list(self) -> builtins.list[Pipeline]: ...

    def get(self, type_id: str) -> Pipeline | None: ...


class ProviderCatalog(Protocol):
    def descriptors(self) -> list[ProviderDescriptor]: ...

    def secrets(self) -> list[SecretDefinition]: ...

    def option_errors(self, configs: Sequence[ProviderConfig]) -> dict[str, str]: ...

    def resolver(self, configs: Sequence[ProviderConfig]) -> ProviderResolver: ...
