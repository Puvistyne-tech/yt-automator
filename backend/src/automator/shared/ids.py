from __future__ import annotations

import re
import uuid

OPAQUE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def random_id(prefix: str = "") -> str:
    token = uuid.uuid4().hex
    return f"{prefix}_{token}" if prefix else token


def is_opaque_id(value: str) -> bool:
    return bool(OPAQUE_ID.match(value))
