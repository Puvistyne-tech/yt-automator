from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping

from autotube.shared.hashing import hmac_sha256_hex, same_digest

SEPARATOR = "."


def encode_payload(payload: Mapping[str, str]) -> str:
    raw = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_payload(body: str) -> dict[str, str] | None:
    try:
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        loaded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return {str(key): str(value) for key, value in loaded.items()}


def sign_payload(payload: Mapping[str, str], key: str) -> str:
    body = encode_payload(payload)
    return f"{body}{SEPARATOR}{hmac_sha256_hex(key, body)}"


def read_unverified(token: str) -> dict[str, str] | None:
    body, separator, _ = token.partition(SEPARATOR)
    return decode_payload(body) if separator else None


def verify_signature(token: str, key: str) -> bool:
    body, separator, signature = token.partition(SEPARATOR)
    return bool(separator) and same_digest(hmac_sha256_hex(key, body), signature)
