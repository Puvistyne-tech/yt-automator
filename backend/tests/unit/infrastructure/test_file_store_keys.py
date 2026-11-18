from __future__ import annotations

import stat
from pathlib import Path

from autotube.infrastructure.secrets.file_store import EncryptedFileSecretStore, shared_key


def file_store(folder: Path) -> EncryptedFileSecretStore:
    return EncryptedFileSecretStore(folder / "secrets.enc", folder / "secrets.key")


def test_a_store_built_before_the_key_reads_what_another_wrote(tmp_path: Path) -> None:
    writer, reader = file_store(tmp_path), file_store(tmp_path)
    writer.set("api", "value")
    assert reader.get("api") == "value"


def test_two_first_writers_share_one_key(tmp_path: Path) -> None:
    first, second = file_store(tmp_path), file_store(tmp_path)
    first.set("a", "one")
    second.set("b", "two")
    fresh = file_store(tmp_path)
    assert (fresh.get("a"), fresh.get("b")) == ("one", "two")
    assert first.get("b") == "two"


def test_the_key_is_created_once_and_privately(tmp_path: Path) -> None:
    key_path = tmp_path / "nested" / "secrets.key"
    created = shared_key(key_path)
    assert shared_key(key_path) == created
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
