from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from autotube.domain.port_catalogs import ProviderCatalog
from autotube.domain.port_runtime import SecretStore
from autotube.domain.providers import ProviderConfig, ProviderDescriptor
from autotube.domain.secrets import SecretDefinition
from autotube.infrastructure.providers.context import ProviderContext
from autotube.infrastructure.providers.option_validation import config_option_errors
from autotube.infrastructure.providers.registry import ALL_SPECS, AnySpec
from autotube.infrastructure.providers.resolver import ChainResolver
from autotube.infrastructure.providers.secret_definitions import PROVIDER_SECRETS


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

    def option_errors(self, configs: Sequence[ProviderConfig]) -> dict[str, str]:
        return config_option_errors(self.specs, configs)

    def resolver(self, configs: Sequence[ProviderConfig]) -> ChainResolver:
        names = [definition.name for definition in self.secret_definitions]
        return ChainResolver(self.specs, configs, self.context, names)


def build_provider_catalog(secrets: SecretStore, data_dir: Path) -> ProviderCatalog:
    return LocalProviderCatalog(ProviderContext(secrets=secrets, data_dir=data_dir))
