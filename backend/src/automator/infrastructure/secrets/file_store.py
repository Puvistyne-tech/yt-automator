from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from cryptography.fernet import Fernet

PRIVATE_FILE_MODE = 0o600


def write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, PRIVATE_FILE_MODE)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    temporary.chmod(PRIVATE_FILE_MODE)
    temporary.replace(path)


def load_or_create_key(key_path: Path) -> bytes:
    if key_path.exists():
        return key_path.read_bytes().strip()
    key = Fernet.generate_key()
    write_private(key_path, key)
    return key


class EncryptedFileSecretStore:
    def __init__(self, path: Path, key_path: Path) -> None:
        self.path = path
        self.fernet = Fernet(load_or_create_key(key_path))
        self.lock = threading.Lock()

    def read_all(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        loaded = json.loads(self.fernet.decrypt(self.path.read_bytes()))
        return {str(key): str(value) for key, value in loaded.items()}

    def write_all(self, values: dict[str, str]) -> None:
        write_private(self.path, self.fernet.encrypt(json.dumps(values).encode("utf-8")))

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
