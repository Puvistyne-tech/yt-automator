from __future__ import annotations

from pathlib import Path

import keyring
from keyring.backend import KeyringBackend
from keyring.backends import fail

from autotube.domain.ports import SecretStore
from autotube.infrastructure.config import SecretBackend
from autotube.infrastructure.secrets.file_store import EncryptedFileSecretStore
from autotube.infrastructure.secrets.keyring_store import KeyringSecretStore

SECRETS_FILE = "secrets.enc"
KEY_FILE = "secrets.key"


def usable_keyring(backend: KeyringBackend) -> bool:
    return not isinstance(backend, fail.Keyring) and backend.priority > 0


def file_store(data_dir: Path) -> EncryptedFileSecretStore:
    return EncryptedFileSecretStore(data_dir / SECRETS_FILE, data_dir / KEY_FILE)


def build_secret_store(
    choice: SecretBackend,
    data_dir: Path,
    service: str,
    backend: KeyringBackend | None = None,
) -> SecretStore:
    detected = backend or keyring.get_keyring()
    if choice is SecretBackend.KEYRING:
        return KeyringSecretStore(service, detected)
    if choice is SecretBackend.AUTO and usable_keyring(detected):
        return KeyringSecretStore(service, detected)
    return file_store(data_dir)
