from __future__ import annotations

import unicodedata


def comparable(text: str) -> str:
    composed = unicodedata.normalize("NFC", text).casefold()
    kept = "".join(char for char in composed if not unicodedata.category(char).startswith("P"))
    return " ".join(kept.split())


def edit_distance(first: str, second: str) -> int:
    previous = list(range(len(second) + 1))
    for row, char in enumerate(first, start=1):
        current = [row]
        for column, other in enumerate(second, start=1):
            substitution = previous[column - 1] + (char != other)
            current.append(min(previous[column] + 1, current[column - 1] + 1, substitution))
        previous = current
    return previous[-1]


def character_error_rate(reference: str, heard: str) -> float:
    expected, actual = comparable(reference), comparable(heard)
    if not expected:
        return 0.0 if not actual else 1.0
    return edit_distance(expected, actual) / len(expected)
