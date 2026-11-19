from __future__ import annotations

import builtins
from collections.abc import Sequence
from typing import Protocol

from autotube.domain.pipeline import Pipeline, ProviderResolver
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.providers import ProviderConfig, ProviderDescriptor
from autotube.domain.secrets import SecretDefinition


class PipelineRegistry(Protocol):
    def list(self) -> builtins.list[Pipeline]: ...

    def get(self, type_id: str) -> Pipeline | None: ...


class EngineCatalog(Protocol):
    def list(self) -> builtins.list[PipelineEngine]: ...

    def get(self, engine_id: str) -> PipelineEngine | None: ...


class ProviderCatalog(Protocol):
    def descriptors(self) -> list[ProviderDescriptor]: ...

    def secrets(self) -> list[SecretDefinition]: ...

    def option_errors(self, configs: Sequence[ProviderConfig]) -> dict[str, str]: ...

    def resolver(self, configs: Sequence[ProviderConfig]) -> ProviderResolver: ...
