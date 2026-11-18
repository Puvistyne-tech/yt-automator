from __future__ import annotations

from automator.application.lookups import require
from automator.domain.ports import ProviderCatalog
from automator.domain.secrets import SecretDefinition


def known_secret(catalog: ProviderCatalog, name: str) -> SecretDefinition:
    found = next((secret for secret in catalog.secrets() if secret.name == name), None)
    return require(found, "secret", name)
