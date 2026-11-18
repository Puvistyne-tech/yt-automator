from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from automator.domain.port_catalogs import ProviderCatalog
from automator.domain.port_runtime import SecretStore
from automator.domain.providers import ProviderConfig, ProviderDescriptor
from automator.domain.secrets import SecretDefinition
from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.registry import ALL_SPECS, AnySpec
from automator.infrastructure.providers.resolver import ChainResolver
from automator.infrastructure.providers.secret_definitions import PROVIDER_SECRETS


class LocalProviderCatalog:
    def __init__(
        self,
        context: ProviderContext,
        specs: Sequence[AnySpec] = ALL_SPECS,
        secret_definitions: Sequence[SecretDefinition] = PROVIDER_SECRETS,
    ) -> None:
        self.context = context
        self.specs = {spec.provider_id: spec for spec in specs}
        self.secret_definitions = list(secret_definitions)

    def descriptors(self) -> list[ProviderDescriptor]:
        return [
            spec.descriptor(spec.default(self.context).available()) for spec in self.specs.values()
        ]

    def secrets(self) -> list[SecretDefinition]:
        return list(self.secret_definitions)

    def resolver(self, configs: Sequence[ProviderConfig]) -> ChainResolver:
        return ChainResolver(self.specs, configs, self.context)


def build_provider_catalog(secrets: SecretStore, data_dir: Path) -> ProviderCatalog:
    return LocalProviderCatalog(ProviderContext(secrets=secrets, data_dir=data_dir))
