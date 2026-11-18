from __future__ import annotations

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError


class KeyringSecretStore:
    def __init__(self, service: str, backend: KeyringBackend | None = None) -> None:
        self.service = service
        self.backend = backend or keyring.get_keyring()

    def get(self, name: str) -> str | None:
        return self.backend.get_password(self.service, name)

    def set(self, name: str, value: str) -> None:
        self.backend.set_password(self.service, name, value)

    def delete(self, name: str) -> None:
        try:
            self.backend.delete_password(self.service, name)
        except PasswordDeleteError:
            return

    def has(self, name: str) -> bool:
        return self.get(name) is not None
