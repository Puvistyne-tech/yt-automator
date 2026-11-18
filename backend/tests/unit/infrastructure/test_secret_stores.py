from __future__ import annotations

import stat
from collections.abc import Callable
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from keyring.backend import KeyringBackend
from keyring.backends import fail
from keyring.errors import PasswordDeleteError

from automator.domain.ports import SecretStore
from automator.infrastructure.config import SecretBackend
from automator.infrastructure.secrets.file_store import EncryptedFileSecretStore, SecretsUnreadable
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
    store.set("channel/c1/token", "tok-2")
    assert store.get("channel/c1/token") == "tok-2"
    store.delete("channel/c1/token")
    store.delete("channel/c1/token")
    assert store.get("channel/c1/token") is None
    assert store.get("credential/k/client_secret") == "s3cret"


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_file_store_encrypts_and_restricts_permissions(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    file_store(nested).set("api", "plain-value")
    assert b"plain-value" not in (nested / "secrets.enc").read_bytes()
    assert {mode_of(nested / name) for name in ("secrets.enc", "secrets.key")} == {0o600}
    assert sorted(path.name for path in nested.iterdir()) == ["secrets.enc", "secrets.key"]
    assert file_store(nested).get("api") == "plain-value"


def test_an_existing_loose_key_is_reused_and_tightened(tmp_path: Path) -> None:
    file_store(tmp_path).set("api", "value")
    key = tmp_path / "secrets.key"
    key.chmod(0o644)
    assert file_store(tmp_path).get("api") == "value"
    assert mode_of(key) == 0o600


def lose_key(tmp_path: Path) -> None:
    (tmp_path / "secrets.key").unlink()


def truncate_secrets(tmp_path: Path) -> None:
    (tmp_path / "secrets.enc").write_bytes(b"trunc")


def corrupt_key(tmp_path: Path) -> None:
    (tmp_path / "secrets.key").write_bytes(b"not-a-key")


def store_a_list(tmp_path: Path) -> None:
    key = (tmp_path / "secrets.key").read_bytes()
    (tmp_path / "secrets.enc").write_bytes(Fernet(key).encrypt(b"[1]"))


def store_bad_json(tmp_path: Path) -> None:
    key = (tmp_path / "secrets.key").read_bytes()
    (tmp_path / "secrets.enc").write_bytes(Fernet(key).encrypt(b"{"))


@pytest.mark.parametrize(
    "damage", [lose_key, truncate_secrets, corrupt_key, store_a_list, store_bad_json]
)
def test_unreadable_secrets_raise_a_reconnect_error(
    tmp_path: Path, damage: Callable[[Path], None]
) -> None:
    file_store(tmp_path).set("api", "value")
    damage(tmp_path)
    store = file_store(tmp_path)
    with pytest.raises(SecretsUnreadable, match="reconnect your channels") as raised:
        store.get("api")
    assert raised.value.code == "secrets_unreadable"
    assert "value" not in raised.value.message
    with pytest.raises(SecretsUnreadable):
        store.set("api", "new")


@pytest.mark.parametrize("damage", [lose_key, corrupt_key])
def test_removing_the_unreadable_file_recovers_without_a_restart(
    tmp_path: Path, damage: Callable[[Path], None]
) -> None:
    file_store(tmp_path).set("api", "value")
    damage(tmp_path)
    store = file_store(tmp_path)
    with pytest.raises(SecretsUnreadable) as raised:
        store.get("api")
    assert str(tmp_path / "secrets.enc") in raised.value.message
    assert str(tmp_path / "secrets.key") in raised.value.message
    (tmp_path / "secrets.enc").unlink()
    assert store.get("api") is None
    store.set("api", "new")
    assert store.get("api") == "new"
    assert mode_of(tmp_path / "secrets.key") == 0o600
    assert file_store(tmp_path).get("api") == "new"


class SilentKeyring(MemoryKeyring):
    priority = 0


@pytest.mark.parametrize(
    ("choice", "backend", "expected"),
    [
        (SecretBackend.AUTO, MemoryKeyring(), KeyringSecretStore),
        (SecretBackend.AUTO, fail.Keyring(), EncryptedFileSecretStore),  # type: ignore[no-untyped-call]
        (SecretBackend.AUTO, SilentKeyring(), EncryptedFileSecretStore),
        (SecretBackend.FILE, MemoryKeyring(), EncryptedFileSecretStore),
        (SecretBackend.FILE, fail.Keyring(), EncryptedFileSecretStore),  # type: ignore[no-untyped-call]
        (SecretBackend.KEYRING, MemoryKeyring(), KeyringSecretStore),
    ],
)
def test_selection_prefers_a_working_keychain(
    tmp_path: Path, choice: SecretBackend, backend: KeyringBackend, expected: type
) -> None:
    selected = build_secret_store(choice, tmp_path, SERVICE, backend)
    assert isinstance(selected, expected)
    if isinstance(selected, EncryptedFileSecretStore):
        assert selected.path == tmp_path / "secrets.enc"
        assert (tmp_path / "secrets.key").is_file()
