from __future__ import annotations

from collections.abc import Mapping


def language_candidates(language: str) -> list[str]:
    code = language.strip().lower().replace("_", "-")
    primary = code.split("-")[0]
    return [code] if code == primary else [code, primary]


def lookup_language[T](mapping: Mapping[str, T], language: str) -> T | None:
    lowered = {key.lower(): value for key, value in mapping.items()}
    return next(
        (lowered[key] for key in language_candidates(language) if key in lowered),
        None,
    )
