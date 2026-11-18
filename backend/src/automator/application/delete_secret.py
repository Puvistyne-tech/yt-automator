from __future__ import annotations

from dataclasses import dataclass

from automator.application.known_secret import known_secret
from automator.domain.ports import ProviderCatalog, SecretStore


@dataclass(frozen=True)
class DeleteSecret:
    catalog: ProviderCatalog
    secrets: SecretStore

    def execute(self, name: str) -> None:
        self.secrets.delete(known_secret(self.catalog, name).name)
