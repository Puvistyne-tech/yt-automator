from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from automator.domain.capabilities import Capability
from automator.domain.pipeline import ProviderResolver
from automator.domain.ports import ProviderCatalog, SecretStore
from automator.domain.providers import ProviderConfig, ProviderDescriptor
from automator.domain.secrets import SecretDefinition
from automator.shared.errors import RuleConflict


class UnavailableResolver:
    def resolve(self, capability: Capability) -> Any:
        raise RuleConflict(
            "provider_unavailable", f"no provider is installed for {capability.value}"
        )


class EmptyProviderCatalog:
    def descriptors(self) -> list[ProviderDescriptor]:
        return []

    def secrets(self) -> list[SecretDefinition]:
        return []

    def resolver(self, configs: Sequence[ProviderConfig]) -> ProviderResolver:  # noqa: ARG002
        return UnavailableResolver()


def build_provider_catalog(secrets: SecretStore, data_dir: Path) -> ProviderCatalog:  # noqa: ARG001
    return EmptyProviderCatalog()
