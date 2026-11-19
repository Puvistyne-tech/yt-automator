from __future__ import annotations

from functools import cache

from pydantic import TypeAdapter

from autotube.pipelines.narrated_video.resources import resource_json
from autotube.pipelines.narrated_video.story.words import contains_phrase

TERMS_BY_LANGUAGE = TypeAdapter(dict[str, list[str]])


@cache
def child_terms() -> tuple[str, ...]:
    loaded = TERMS_BY_LANGUAGE.validate_python(resource_json("story", "child_terms.json"))
    return tuple(term for terms in loaded.values() for term in terms)


def child_terms_in(text: str) -> list[str]:
    return [term for term in child_terms() if contains_phrase(text, term)]


def child_term_message(found: list[str]) -> str:
    return f"never address children; remove: {', '.join(found)}"
