from __future__ import annotations

from autotube.shared.hashing import sha256_hex


def prompt_seed(prompt: str, seed: int | None = None) -> int:
    return seed if seed is not None else int(sha256_hex(prompt)[:8], 16)
