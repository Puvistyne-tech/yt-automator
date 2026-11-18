from __future__ import annotations

import hashlib
import hmac
import json


def as_bytes(value: bytes | str) -> bytes:
    return value.encode("utf-8") if isinstance(value, str) else value


def sha256_hex(value: bytes | str) -> str:
    return hashlib.sha256(as_bytes(value)).hexdigest()


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def stable_hash(value: object) -> str:
    return sha256_hex(stable_json(value))


def hmac_sha256_hex(key: bytes | str, message: bytes | str) -> str:
    return hmac.new(as_bytes(key), as_bytes(message), hashlib.sha256).hexdigest()


def same_digest(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
