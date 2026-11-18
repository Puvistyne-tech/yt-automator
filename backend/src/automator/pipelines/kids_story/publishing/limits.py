from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from automator.pipelines.kids_story.text.graphemes import grapheme_clusters

TITLE_MAX = 100
DESCRIPTION_MAX_BYTES = 5000
TAGS_MAX = 500
ELLIPSIS = "…"
FORBIDDEN = re.compile(r"[<>]")
TRAILING = " ,.;:-|"

Measure = Callable[[str], int]


def cleaned(text: str) -> str:
    return FORBIDDEN.sub("", text).strip()


def utf8_length(text: str) -> int:
    return len(text.encode("utf-8"))


def longest_head(clusters: Sequence[str], limit: int, measure: Measure) -> str:
    kept: list[str] = []
    used = measure(ELLIPSIS)
    for cluster in clusters:
        used += measure(cluster)
        if used > limit:
            break
        kept.append(cluster)
    return "".join(kept)


def word_boundary(head: str) -> str:
    space = head.rfind(" ")
    return head[:space] if space > len(head) // 2 else head


def truncated_by(text: str, limit: int, measure: Measure) -> str:
    if measure(text) <= limit:
        return text
    head = longest_head(grapheme_clusters(text), limit, measure)
    return word_boundary(head).rstrip(TRAILING) + ELLIPSIS


def truncated(text: str, limit: int) -> str:
    return truncated_by(text, limit, len)


def truncated_bytes(text: str, limit: int) -> str:
    return truncated_by(text, limit, utf8_length)


def tag_cost(tag: str) -> int:
    return len(tag) + (2 if " " in tag else 0)


def tags_length(tags: Sequence[str]) -> int:
    return sum(tag_cost(tag) for tag in tags) + max(len(tags) - 1, 0)


def tags_within(tags: Sequence[str], limit: int = TAGS_MAX) -> list[str]:
    kept: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        tag = cleaned(raw).replace(",", " ").strip()
        if not tag or tag.casefold() in seen:
            continue
        if tags_length([*kept, tag]) <= limit:
            kept.append(tag)
            seen.add(tag.casefold())
    return kept
