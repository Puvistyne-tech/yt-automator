from __future__ import annotations

from collections.abc import Callable

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

from automator.infrastructure.secrets.unreadable import keychain_unreadable


def guarded[T](call: Callable[[], T]) -> T:
    try:
        return call()
    except PasswordDeleteError:
        raise
    except KeyringError as failure:
        raise keychain_unreadable(failure) from failure


class KeyringSecretStore:
    def __init__(self, service: str, backend: KeyringBackend | None = None) -> None:
        self.service = service
        self.backend = backend or keyring.get_keyring()

    def get(self, name: str) -> str | None:
        return guarded(lambda: self.backend.get_password(self.service, name))

    def set(self, name: str, value: str) -> None:
        guarded(lambda: self.backend.set_password(self.service, name, value))

    def delete(self, name: str) -> None:
        try:
            guarded(lambda: self.backend.delete_password(self.service, name))
        except PasswordDeleteError:
            return

    def has(self, name: str) -> bool:
        return self.get(name) is not None
