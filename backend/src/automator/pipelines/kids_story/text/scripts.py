from __future__ import annotations

TAMIL_BLOCK = range(0x0B80, 0x0C00)


def script_language(text: str) -> str:
    return "ta" if any(ord(character) in TAMIL_BLOCK for character in text) else "en"
