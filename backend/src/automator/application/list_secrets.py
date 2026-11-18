from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import ProviderCatalog, SecretStore
from automator.domain.secrets import SecretStatus


@dataclass(frozen=True)
class ListSecrets:
    catalog: ProviderCatalog
    secrets: SecretStore

    def execute(self) -> list[SecretStatus]:
        return [
            SecretStatus(**definition.model_dump(), is_set=self.secrets.has(definition.name))
            for definition in self.catalog.secrets()
        ]
