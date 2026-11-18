from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import ProviderCatalog, ProviderConfigRepository
from automator.domain.providers import ProvidersView


@dataclass(frozen=True)
class GetProviders:
    catalog: ProviderCatalog
    configs: ProviderConfigRepository

    def execute(self) -> ProvidersView:
        return ProvidersView(
            descriptors=tuple(self.catalog.descriptors()), config=tuple(self.configs.list())
        )
