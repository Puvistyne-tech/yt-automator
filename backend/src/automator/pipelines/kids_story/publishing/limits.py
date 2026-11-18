from __future__ import annotations

import re
from collections.abc import Sequence

TITLE_MAX = 100
DESCRIPTION_MAX = 5000
TAGS_MAX = 500
ELLIPSIS = "…"
FORBIDDEN = re.compile(r"[<>]")


def cleaned(text: str) -> str:
    return FORBIDDEN.sub("", text).strip()


def truncated(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - len(ELLIPSIS)]
    space = cut.rfind(" ")
    head = cut[:space] if space > limit // 2 else cut
    return head.rstrip(" ,.;:-|") + ELLIPSIS


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
