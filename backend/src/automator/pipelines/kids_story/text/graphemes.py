from __future__ import annotations

import unicodedata

JOINERS = frozenset({"‌", "‍"})


def extends_cluster(character: str) -> bool:
    return character in JOINERS or unicodedata.category(character).startswith("M")


def grapheme_clusters(text: str) -> list[str]:
    clusters: list[str] = []
    for character in text:
        if clusters and extends_cluster(character):
            clusters[-1] += character
        else:
            clusters.append(character)
    return clusters


def grapheme_length(text: str) -> int:
    return len(grapheme_clusters(text))
