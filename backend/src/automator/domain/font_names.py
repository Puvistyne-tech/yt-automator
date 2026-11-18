from __future__ import annotations

FONT_NAME_EXTRAS = frozenset(" -_")


def safe_font_family(family: str) -> bool:
    return bool(family) and all(char.isalnum() or char in FONT_NAME_EXTRAS for char in family)
