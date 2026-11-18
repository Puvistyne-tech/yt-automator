from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from autotube.domain.ports import ProviderCatalog, ProviderConfigRepository
from autotube.domain.providers import ProviderConfig, provider_config_errors
from autotube.shared.errors import raise_if_invalid


@dataclass(frozen=True)
class SaveProviderConfig:
    catalog: ProviderCatalog
    configs: ProviderConfigRepository

    def execute(self, configs: Sequence[ProviderConfig]) -> list[ProviderConfig]:
        errors = provider_config_errors(configs, self.catalog.descriptors())
        raise_if_invalid(errors | self.catalog.option_errors(configs))
        self.configs.save_all(configs)
        return self.configs.list()
