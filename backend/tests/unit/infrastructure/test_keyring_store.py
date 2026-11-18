from __future__ import annotations

import pytest
from keyring.backend import KeyringBackend
from keyring.errors import KeyringLocked

from automator.infrastructure.secrets.keyring_store import KeyringSecretStore
from automator.infrastructure.secrets.unreadable import SecretsUnreadable


class LockedKeyring(KeyringBackend):
    priority = 1

    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringLocked(f"{service}/{username} is locked")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringLocked(f"{service}/{username} is locked, {len(password)} characters refused")

    def delete_password(self, service: str, username: str) -> None:
        raise KeyringLocked(f"{service}/{username} is locked")


def locked_store() -> KeyringSecretStore:
    return KeyringSecretStore("automator-test", LockedKeyring())  # type: ignore[no-untyped-call]


@pytest.mark.parametrize("action", ["get", "has", "set", "delete"])
def test_a_locked_keychain_raises_secrets_unreadable(action: str) -> None:
    arguments = ("api", "value-123") if action == "set" else ("api",)
    with pytest.raises(SecretsUnreadable, match="KeyringLocked") as raised:
        getattr(locked_store(), action)(*arguments)
    assert raised.value.code == "secrets_unreadable"
    assert "value-123" not in raised.value.message
