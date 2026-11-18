from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from automator.domain.ports import ProviderCatalog, ProviderConfigRepository
from automator.domain.providers import ProviderConfig, provider_config_errors
from automator.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class SaveProviderConfig:
    catalog: ProviderCatalog
    configs: ProviderConfigRepository

    def execute(self, configs: Sequence[ProviderConfig]) -> list[ProviderConfig]:
        raise_if_invalid(provider_config_errors(configs, self.catalog.descriptors()))
        self.configs.save_all(configs)
        return self.configs.list()
