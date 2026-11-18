from __future__ import annotations

import stat
from pathlib import Path

import pytest
from keyring.backend import KeyringBackend
from keyring.backends import fail
from keyring.errors import PasswordDeleteError

from automator.domain.ports import SecretStore
from automator.infrastructure.config import SecretBackend
from automator.infrastructure.secrets.file_store import EncryptedFileSecretStore
from automator.infrastructure.secrets.keyring_store import KeyringSecretStore
from automator.infrastructure.secrets.selection import build_secret_store

SERVICE = "automator-test"


class MemoryKeyring(KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if self.values.pop((service, username), None) is None:
            raise PasswordDeleteError(username)


def file_store(tmp_path: Path) -> EncryptedFileSecretStore:
    return EncryptedFileSecretStore(tmp_path / "secrets.enc", tmp_path / "secrets.key")


def keyring_store(_: Path) -> KeyringSecretStore:
    return KeyringSecretStore(SERVICE, MemoryKeyring())


@pytest.fixture(params=[file_store, keyring_store], ids=["file", "keyring"])
def store(request: pytest.FixtureRequest, tmp_path: Path) -> SecretStore:
    factory = request.param
    created: SecretStore = factory(tmp_path)
    return created


def test_store_sets_reads_and_deletes(store: SecretStore) -> None:
    assert store.get("channel/c1/token") is None
    assert not store.has("channel/c1/token")
    store.set("channel/c1/token", "tok-1")
    store.set("credential/k/client_secret", "s3cret")
    assert store.get("channel/c1/token") == "tok-1"
    assert store.has("credential/k/client_secret")
    store.delete("channel/c1/token")
    store.delete("channel/c1/token")
    assert store.get("channel/c1/token") is None
    assert store.get("credential/k/client_secret") == "s3cret"


def test_file_store_encrypts_and_restricts_permissions(tmp_path: Path) -> None:
    file_store(tmp_path).set("api", "plain-value")
    assert b"plain-value" not in (tmp_path / "secrets.enc").read_bytes()
    for name in ("secrets.enc", "secrets.key"):
        assert stat.S_IMODE((tmp_path / name).stat().st_mode) == 0o600
    assert file_store(tmp_path).get("api") == "plain-value"


@pytest.mark.parametrize(
    ("choice", "backend", "expected"),
    [
        (SecretBackend.AUTO, MemoryKeyring(), KeyringSecretStore),
        (SecretBackend.AUTO, fail.Keyring(), EncryptedFileSecretStore),  # type: ignore[no-untyped-call]
        (SecretBackend.FILE, MemoryKeyring(), EncryptedFileSecretStore),
        (SecretBackend.KEYRING, MemoryKeyring(), KeyringSecretStore),
    ],
)
def test_selection_prefers_a_working_keychain(
    tmp_path: Path, choice: SecretBackend, backend: KeyringBackend, expected: type
) -> None:
    assert isinstance(build_secret_store(choice, tmp_path, SERVICE, backend), expected)
