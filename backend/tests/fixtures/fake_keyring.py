from __future__ import annotations

from keyring.backend import KeyringBackend
from keyring.errors import KeyringLocked

from autotube.infrastructure.secrets.keyring_store import KeyringSecretStore


class LockedKeyring(KeyringBackend):
    priority = 1

    def get_password(self, service: str, username: str) -> str | None:
        raise KeyringLocked(f"{service}/{username} is locked")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise KeyringLocked(f"{service}/{username} is locked, {len(password)} characters refused")

    def delete_password(self, service: str, username: str) -> None:
        raise KeyringLocked(f"{service}/{username} is locked")


def locked_store() -> KeyringSecretStore:
    return KeyringSecretStore("autotube-test", LockedKeyring())  # type: ignore[no-untyped-call]
