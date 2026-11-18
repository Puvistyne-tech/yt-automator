from __future__ import annotations

import json
import os
import stat
import threading
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from autotube.infrastructure.secrets.unreadable import SecretsUnreadable, file_unreadable

PRIVATE_FILE_MODE = 0o600


def write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, PRIVATE_FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    temporary.chmod(PRIVATE_FILE_MODE)
    temporary.replace(path)


def tighten(path: Path) -> None:
    if stat.S_IMODE(path.stat().st_mode) != PRIVATE_FILE_MODE:
        path.chmod(PRIVATE_FILE_MODE)


def load_key(key_path: Path) -> bytes | None:
    if not key_path.exists():
        return None
    tighten(key_path)
    return key_path.read_bytes().strip()


def shared_key(key_path: Path) -> bytes:
    key_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(key_path, flags, PRIVATE_FILE_MODE)
    except FileExistsError:
        return load_key(key_path) or b""
    key = Fernet.generate_key()
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(key)
    return key


def fresh_fernet(key_path: Path) -> Fernet:
    key = Fernet.generate_key()
    write_private(key_path, key)
    return Fernet(key)


def fernet_for(key: bytes | None) -> Fernet | None:
    try:
        return Fernet(key) if key is not None else None
    except ValueError:
        return None


class EncryptedFileSecretStore:
    def __init__(self, path: Path, key_path: Path) -> None:
        self.path = path
        self.key_path = key_path
        self.fernet = fernet_for(load_key(key_path))
        self.lock = threading.Lock()

    def unreadable(self) -> SecretsUnreadable:
        return file_unreadable(self.path, self.key_path)

    def decrypted(self) -> bytes:
        self.fernet = self.fernet or fernet_for(load_key(self.key_path))
        if self.fernet is None:
            raise self.unreadable()
        try:
            return self.fernet.decrypt(self.path.read_bytes())
        except InvalidToken as error:
            raise self.unreadable() from error

    def writer(self) -> Fernet:
        if self.fernet is None or not self.key_path.exists():
            shared = fernet_for(shared_key(self.key_path))
            self.fernet = shared or fresh_fernet(self.key_path)
        return self.fernet

    def read_all(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            loaded = json.loads(self.decrypted())
        except ValueError as error:
            raise self.unreadable() from error
        if not isinstance(loaded, dict):
            raise self.unreadable()
        return {str(key): str(value) for key, value in loaded.items()}

    def write_all(self, values: dict[str, str]) -> None:
        encrypted = self.writer().encrypt(json.dumps(values).encode("utf-8"))
        write_private(self.path, encrypted)

    def get(self, name: str) -> str | None:
        with self.lock:
            return self.read_all().get(name)

    def set(self, name: str, value: str) -> None:
        with self.lock:
            self.write_all(self.read_all() | {name: value})

    def delete(self, name: str) -> None:
        with self.lock:
            values = self.read_all()
            if values.pop(name, None) is not None:
                self.write_all(values)

    def has(self, name: str) -> bool:
        return self.get(name) is not None
