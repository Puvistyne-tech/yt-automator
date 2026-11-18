from __future__ import annotations

from dataclasses import dataclass

from autotube.application.known_secret import known_secret
from autotube.domain.ports import ProviderCatalog, SecretStore
from autotube.shared.errors import ValidationFailed


@dataclass(frozen=True)
class SetSecret:
    catalog: ProviderCatalog
    secrets: SecretStore

    def execute(self, name: str, value: str) -> None:
        definition = known_secret(self.catalog, name)
        if not value.strip():
            raise ValidationFailed({"value": "must not be empty"})
        self.secrets.set(definition.name, value)
